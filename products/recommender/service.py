from __future__ import annotations

from products.models import Product, UserProfile

from .explanations import build_explanations
from .planner import create_style_plan, GENDER_BY_PROMPT
from .reranker import rerank_candidates
from .retrieval import retrieve_candidates
from .schemas import RecommendationResult, RerankChoice
from .scoring import score_candidates
from .validator import validate_rerank_choice


APPAREL_TERMS = {
    "shirt", "shirts", "blazer", "blazers", "trouser", "trousers", "chinos",
    "suit", "suits", "saree", "sarees", "lehenga", "kurta", "jacket", "jeans",
    "dress", "top", "tshirt", "t-shirt", "shorts", "hoodie", "sweatshirt",
    "formal", "casual", "ethnic", "traditional", "office", "wedding", "party",
    "gym", "sportswear", "outfit", "clothes", "clothing", "wear",
}
NON_APPAREL_TERMS = {
    "laptop", "phone", "mobile", "rtx", "graphics", "processor", "camera",
    "headphone", "furniture", "book", "software", "game", "gaming",
}


import re as _re


def _unsupported_prompt(prompt: str, plan) -> bool:
    prompt_lower = (prompt or "").lower()
    if not prompt_lower:
        return False
    prompt_words = set(_re.findall(r"[a-z0-9]+", prompt_lower))
    has_apparel = bool(prompt_words & APPAREL_TERMS)
    has_non_apparel = bool(prompt_words & NON_APPAREL_TERMS)
    return has_non_apparel and not has_apparel



def recommend_for_profile(
    profile: UserProfile | None,
    prompt: str,
    selected_gender: str = "all",
    max_results: int = 12,
) -> RecommendationResult:
    plan = create_style_plan(prompt, profile, selected_gender)

    # Ensure profile gender locking and tab-based locking when undiagnosed
    lock_gender = None
    if profile and profile.gender in {"men", "women", "kids"}:
        lock_gender = profile.gender
    elif selected_gender in {"men", "women", "kids"}:
        # Undiagnosed state with a specific gender tab selected
        lock_gender = selected_gender

    if lock_gender and prompt:
        prompt_lower = prompt.lower()
        # Find raw words in the query prompt
        prompt_words = set(_re.findall(r"[a-z0-9]+", prompt_lower))
        
        # Check if the user is explicitly requesting styling for other genders
        requested_other_gender = False
        other_gender_name = ""
        for g, terms in GENDER_BY_PROMPT.items():
            if g != lock_gender and any(term in prompt_words for term in terms):
                requested_other_gender = True
                other_gender_name = g
                break
                
        if requested_other_gender:
            workspace_name = "diagnosed DNA" if (profile and profile.gender != "all") else f"active {lock_gender.title()}'s selection"
            response = (
                f"Your styling workspace is locked to your {workspace_name}. "
                f"We cannot show {other_gender_name} clothing here. "
                f"To change styling categories, please reset your styling state."
            )
            return RecommendationResult(
                products=[],
                plan=plan,
                explanations={},
                scores={},
                rejected=[{"reason": f"Blocked requests for other gender: {other_gender_name}"}],
                stylist_response=response,
            )

    if _unsupported_prompt(prompt, plan):
        response = (
            "I could not find an apparel styling need in this request, so I did not return catalog products. "
            "Ask for clothing, footwear, or outfit styling to get recommendations."
        )
        return RecommendationResult(
            products=[],
            plan=plan,
            explanations={},
            scores={},
            rejected=[{"reason": "Request is outside the apparel catalog"}],
            stylist_response=response,
        )

    candidates, semantic_scores = retrieve_candidates(plan, profile, prompt, max_candidates=70)
    scores = score_candidates(candidates, plan, profile, semantic_scores)
    ranked_products = sorted(candidates, key=lambda product: scores[product.id].total, reverse=True)
    choices, rejected = rerank_candidates(plan, profile, prompt, ranked_products, scores, max_results=max_results)

    products_by_id: dict[int, Product] = {product.id: product for product in ranked_products}
    selected_products = []
    explanations = {}
    seen = set()

    for choice in choices:
        product = products_by_id.get(choice.product_id)
        if not product or product.id in seen:
            continue
        ok, reason = validate_rerank_choice(product, choice, plan, profile)
        if not ok:
            rejected.append({"id": product.id, "reason": reason})
            continue

        score = scores[product.id]
        product.match_score = int(round(min(max(choice.confidence, 0.0), 0.95) * 100))
        product.match_score = max(50, min(95, product.match_score))
        product.match_explanations = build_explanations(product, score, choice)
        explanations[product.id] = product.match_explanations
        selected_products.append(product)
        seen.add(product.id)
        if len(selected_products) >= max_results:
            break

    if len(selected_products) < max_results:
        used_ids = {product.id for product in selected_products}
        backfill_threshold = 0.18 if prompt else 0.0
        for product in ranked_products:
            if product.id in used_ids or scores[product.id].total < backfill_threshold:
                continue
            confidence = max(min(max(scores[product.id].total + 0.35, 0.0), 0.95), plan.minimum_confidence)
            choice = RerankChoice(
                product_id=product.id,
                confidence=confidence,
                reason="Selected by ML compatibility scoring after validation.",
            )
            ok, reason = validate_rerank_choice(product, choice, plan, profile)
            if not ok:
                rejected.append({"id": product.id, "reason": reason})
                continue
            product.match_score = int(round(choice.confidence * 100))
            product.match_score = max(50, min(95, product.match_score))
            product.match_explanations = build_explanations(product, scores[product.id], choice)
            explanations[product.id] = product.match_explanations
            selected_products.append(product)
            used_ids.add(product.id)
            if len(selected_products) >= max_results:
                break

    # Second pass: ensure at least 6 recommendations (or max_results if max_results < 6)
    target_min = min(6, max_results)
    if len(selected_products) < target_min:
        used_ids = {product.id for product in selected_products}
        for product in ranked_products:
            if product.id in used_ids:
                continue
            confidence = max(min(max(scores[product.id].total + 0.35, 0.0), 0.95), plan.minimum_confidence)
            choice = RerankChoice(
                product_id=product.id,
                confidence=confidence,
                reason="Selected by ML compatibility scoring after validation.",
            )
            ok, reason = validate_rerank_choice(product, choice, plan, profile)
            if not ok:
                rejected.append({"id": product.id, "reason": reason})
                continue
            product.match_score = int(round(choice.confidence * 100))
            product.match_score = max(50, min(95, product.match_score))
            product.match_explanations = build_explanations(product, scores[product.id], choice)
            explanations[product.id] = product.match_explanations
            selected_products.append(product)
            used_ids.add(product.id)
            if len(selected_products) >= max_results:
                break

    stylist_response = plan.stylist_response or (
        "I matched your request against the live catalog, scored compatible products, "
        "and kept only validated recommendations."
    )
    if not selected_products:
        stylist_response = (
            "I could not find products that passed the relevance and safety checks for this request. "
            "Try widening the occasion, budget, or garment type."
        )

    return RecommendationResult(
        products=selected_products,
        plan=plan,
        explanations=explanations,
        scores=scores,
        rejected=rejected,
        stylist_response=stylist_response,
    )

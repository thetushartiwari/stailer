from __future__ import annotations

from products.models import Product, UserProfile
from products.recommendation_model import get_color_similarity
from products.stylist_engine import SKIN_TONE_COLORS

import random
from .feedback import feedback_score, _preference_queryset
from .schemas import CandidateScore, StylePlan


BODY_FIT_TERMS = {
    # Female silhouettes
    "hourglass": ("tailored", "fit", "flare", "saree", "lehenga", "bodycon", "midi", "blouse"),
    "pear": ("a-line", "relaxed", "skirt", "high-waisted", "palazzo", "flare"),
    "apple": ("relaxed", "empire", "loose", "straight", "tunic", "flowy"),
    "rectangle": ("structured", "layered", "jacket", "blazer", "fit", "flare"),
    "inverted triangle": ("v-neck", "wrap", "wide-leg", "soft", "draped"),
    "petite": ("slim", "short", "cropped", "tshirt", "jumpsuit"),
    
    # Male silhouettes
    "v-taper": ("structured", "tailored", "slim", "blazer", "suit", "jacket", "double-breasted"),
    "trapezoid": ("regular", "slim", "chinos", "shirt", "polo", "classic"),
    "triangle": ("structured shoulder", "vertical stripe", "straight", "loose", "relaxed"),
    "oval": ("relaxed", "vertical stripe", "loose", "straight", "dark color", "black"),
    
    # Fallback silhouettes
    "athletic": ("structured", "tailored", "slim", "blazer", "suit", "trouser", "formal shirt", "jacket"),
    "round": ("relaxed", "a-line", "anarkali", "loose", "palazzo", "straight"),
}


def _quality_score(product: Product) -> float:
    rating = product.rating or 0.0
    return min(max(rating / 5.0, 0.0), 1.0)


def _skin_score(product: Product, profile: UserProfile | None, plan: StylePlan) -> tuple[float, list[str]]:
    colors = [item.lower() for item in (product.colors or [])]
    reasons = []
    score = 0.0

    if plan.preferred_colors:
        requested = get_color_similarity(colors, plan.preferred_colors)
        score = max(score, requested)
        if requested > 0:
            reasons.append("Matches requested color direction")

    skin = (getattr(profile, "skin_tone", "") or "").lower()
    if skin in SKIN_TONE_COLORS:
        harmony = get_color_similarity(colors, SKIN_TONE_COLORS[skin])
        score = max(score, harmony)
        if harmony > 0:
            reasons.append(f"Color palette suits {skin} skin tone")

    return score, reasons


def _body_score(product: Product, profile: UserProfile | None, plan: StylePlan) -> tuple[float, list[str]]:
    body = (getattr(profile, "body_type", "") or "").lower()
    text = " ".join(
        [
            product.title or "",
            product.category or "",
            product.category_type or "",
            product.description or "",
            product.fit or "",
            " ".join(product.style_tags or []),
            " ".join(plan.fit_strategy),
        ]
    ).lower()
    terms = BODY_FIT_TERMS.get(body, ())
    if not terms:
        return 0.0, []
    if any(term in text for term in terms):
        return 1.0, [f"Fit and silhouette align with {body} body type"]
    return 0.0, []


def _metadata_score(product: Product, plan: StylePlan) -> tuple[float, list[str]]:
    score = 0.0
    reasons = []
    category = (product.category or "").lower()
    category_type = product.category_type or ""

    if category in {item.lower() for item in plan.must_have_categories}:
        score += 0.6
        reasons.append("Matches planned garment category")
    if category_type in plan.preferred_category_types:
        score += 0.4
        reasons.append(f"Matches {category_type} styling context")
    if plan.occasion and plan.occasion in " ".join([product.title, product.description, product.category_type]).lower():
        score += 0.2
    return min(score, 1.0), reasons


def score_candidates(
    products: list[Product],
    plan: StylePlan,
    profile: UserProfile | None,
    semantic_scores: dict[int, float],
) -> dict[int, CandidateScore]:
    skin_tone = getattr(profile, "skin_tone", None)
    body_type = getattr(profile, "body_type", None)
    has_feedback = _preference_queryset(profile).exists() if profile else False
    
    is_empty_state = (
        not plan.style_direction
        and not skin_tone
        and not body_type
        and not has_feedback
    )

    scored = {}
    for product in products:
        skin, skin_reasons = _skin_score(product, profile, plan)
        body, body_reasons = _body_score(product, profile, plan)
        feedback, feedback_reasons = feedback_score(product, profile)
        metadata, metadata_reasons = _metadata_score(product, plan)
        quality = _quality_score(product)
        semantic = semantic_scores.get(product.id, 0.0)

        total = (
            0.36 * semantic
            + 0.22 * metadata
            + 0.16 * body
            + 0.10 * skin
            + 0.10 * quality
            + 0.06 * feedback
        )
        if is_empty_state:
            total += random.uniform(0.0, 1.0)
        reasons = []
        if semantic > 0.12:
            reasons.append("Semantically matches your request")
        reasons.extend(metadata_reasons)
        reasons.extend(body_reasons)
        reasons.extend(skin_reasons)
        reasons.extend(feedback_reasons)
        if quality >= 0.85:
            reasons.append("Strong catalog rating")

        scored[product.id] = CandidateScore(
            product_id=product.id,
            semantic=semantic,
            skin_color=skin,
            body_fit=body,
            feedback=feedback,
            quality=quality,
            metadata=metadata,
            total=total,
            reasons=list(dict.fromkeys(reasons)),
        )
    return scored

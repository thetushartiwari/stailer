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
        if not colors:
            # Fallback for products with empty color lists in sparse catalog
            score = max(score, 0.6)
            reasons.append(f"Color palette suits {skin} skin tone")
        else:
            # Dynamically split skin tone colors to match single-word catalog tokens
            flat_palette = []
            for color in SKIN_TONE_COLORS[skin]:
                flat_palette.extend(color.split())

            harmony = get_color_similarity(colors, flat_palette)
            score = max(score, harmony)
            if harmony > 0:
                # Find the actual matching palette colors dynamically
                matching_palette_colors = []
                for sc in SKIN_TONE_COLORS[skin]:
                    sc_words = sc.split()
                    if any(pc in sc_words for pc in colors):
                        matching_palette_colors.append(sc)
                
                if matching_palette_colors:
                    color_str = ", ".join(sorted(set(matching_palette_colors))).title()
                    reasons.append(f"The {color_str} tones match your {skin.title()} Skin DNA")
                else:
                    reasons.append(f"Color palette suits {skin} skin tone")

    return score, reasons


def _body_score(product: Product, profile: UserProfile | None, plan: StylePlan) -> tuple[float, list[str]]:
    if not profile:
        return 0.0, []

    import re
    body = (getattr(profile, "body_type", "") or "").lower()
    bmi_cat = getattr(profile, "bmi_category", "Normal") or "Normal"
    height = getattr(profile, "height", 0.0) or 0.0
    
    product_text = " ".join(
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

    reasons = []
    score_components = []

    # 1. Structural Silhouette Proportion
    shape_terms = BODY_FIT_TERMS.get(body, ())
    matched_shape_terms = [
        term for term in shape_terms
        if re.search(r"\b" + re.escape(term) + r"\b", product_text)
    ]
    if matched_shape_terms:
        score_components.append(1.0)
        term_str = ", ".join(sorted(set(matched_shape_terms))).title()
        reasons.append(f"The {term_str} detailing flatters your {body.title()} Body DNA")
    else:
        score_components.append(0.0)

    # 2. Scale / BMI Weight Drape
    scale_terms = []
    if bmi_cat in {"Overweight", "Obese"}:
        scale_terms = ["relaxed", "loose", "straight", "vertical stripe", "draped", "flowy", "a-line"]
    elif bmi_cat == "Thin":
        scale_terms = ["slim", "fitted", "cropped", "bodycon", "tight"]
        
    matched_scale_terms = [
        term for term in scale_terms
        if re.search(r"\b" + re.escape(term) + r"\b", product_text)
    ] if scale_terms else []
    if matched_scale_terms:
        score_components.append(1.0)
        scale_str = ", ".join(sorted(set(matched_scale_terms))).title()
        reasons.append(f"The {scale_str} drape fits your {bmi_cat.lower()} proportions")
    else:
        if bmi_cat == "Normal":
            score_components.append(0.8)
        else:
            score_components.append(0.0)

    # 3. Height vertical draping rules
    height_matched = False
    if 0.1 < height < 158.0: # Petite Height
        petite_terms = ["short", "cropped", "vertical", "monochrome", "slim"]
        matched_height_terms = [
            term for term in petite_terms
            if re.search(r"\b" + re.escape(term) + r"\b", product_text)
        ]
        if matched_height_terms:
            score_components.append(1.0)
            height_str = ", ".join(sorted(set(matched_height_terms))).title()
            reasons.append(f"The {height_str} cut visually flatters petite stature")
            height_matched = True
    elif height > 175.0: # Tall Height
        tall_terms = ["maxi", "oversized", "layered", "long", "tunic", "draped"]
        matched_height_terms = [
            term for term in tall_terms
            if re.search(r"\b" + re.escape(term) + r"\b", product_text)
        ]
        if matched_height_terms:
            score_components.append(1.0)
            height_str = ", ".join(sorted(set(matched_height_terms))).title()
            reasons.append(f"The {height_str} proportions fit tall stature")
            height_matched = True

    if not height_matched and height > 0.1:
        score_components.append(0.7)

    # Calculate average biometric fit score
    final_score = sum(score_components) / len(score_components) if score_components else 0.0
    return final_score, reasons


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

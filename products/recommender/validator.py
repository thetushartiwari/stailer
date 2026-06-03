from __future__ import annotations

from products.models import Product, UserProfile

from .schemas import RerankChoice, StylePlan


ADULT_AGE = 16
WOMEN_TERMS = ("women", "woman", "womens", "female", "ladies")
MEN_TERMS = ("men", "mens", " male ")
KIDS_TERMS = ("boys", "boy ", "girls", "girl ", "kids", "kid ", "infant", "junior")


def normalize_audience(value: str | None) -> str:
    value = (value or "all").lower()
    return {
        "male": "men",
        "man": "men",
        "female": "women",
        "woman": "women",
        "child": "kids",
        "children": "kids",
        "kid": "kids",
    }.get(value, value)


def product_text(product: Product) -> str:
    return " ".join(
        [
            product.title or "",
            product.brand or "",
            product.gender or "",
            product.category or "",
            product.category_type or "",
            product.description or "",
            product.product_url or "",
        ]
    ).lower()


def has_audience_contradiction(product: Product) -> bool:
    text = product_text(product)
    gender = normalize_audience(product.gender)
    if gender == "men" and any(term in text for term in WOMEN_TERMS + KIDS_TERMS):
        return True
    if gender == "women" and any(term in text for term in KIDS_TERMS):
        return True
    return False


def validate_candidate(product: Product, plan: StylePlan, profile: UserProfile | None) -> tuple[bool, str]:
    audience = normalize_audience(plan.audience)
    gender = normalize_audience(product.gender)

    if audience in {"men", "women", "kids"} and gender != audience:
        return False, f"wrong audience: expected {audience}, got {gender}"

    age = getattr(profile, "age", None)
    if age is not None and age >= ADULT_AGE and gender == "kids":
        return False, "adult profile cannot receive kids products"

    if not product.image_url or not product.product_url:
        return False, "missing product media or store URL"

    if has_audience_contradiction(product):
        return False, "product text or URL contradicts assigned audience"

    category = (product.category or "").lower()
    if category in {item.lower() for item in plan.avoid_categories}:
        return False, "category is explicitly avoided"

    if plan.budget_max is not None and product.price > plan.budget_max:
        return False, "over budget"

    return True, ""


def validate_rerank_choice(
    product: Product,
    choice: RerankChoice,
    plan: StylePlan,
    profile: UserProfile | None,
) -> tuple[bool, str]:
    ok, reason = validate_candidate(product, plan, profile)
    if not ok:
        return ok, reason
    if choice.confidence < plan.minimum_confidence:
        return False, "AI confidence below threshold"
    return True, ""

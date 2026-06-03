from __future__ import annotations

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from products.models import Product, UserProfile
from products.recommendation_model import build_similarity_matrix

from .schemas import StylePlan
from .validator import normalize_audience, validate_candidate


def product_search_text(product: Product) -> str:
    return " ".join(
        [
            product.title or "",
            product.brand or "",
            product.gender or "",
            product.category or "",
            product.category_type or "",
            product.description or "",
            product.fit or "",
            " ".join(product.colors or []),
            " ".join(product.style_tags or []),
            product.product_url or "",
        ]
    )


def retrieve_candidates(
    plan: StylePlan,
    profile: UserProfile | None,
    prompt: str,
    max_candidates: int = 60,
) -> tuple[list[Product], dict[int, float]]:
    qs = Product.objects.all()
    audience = normalize_audience(plan.audience)
    if audience in {"men", "women", "kids"}:
        qs = qs.filter(gender=audience)
    if plan.budget_max is not None:
        qs = qs.filter(price__lte=plan.budget_max)

    products = []
    for product in qs:
        ok, _ = validate_candidate(product, plan, profile)
        if ok:
            products.append(product)

    if not products:
        return [], {}

    type_filter = {item.lower() for item in plan.preferred_category_types}
    category_filter = {item.lower() for item in plan.must_have_categories}
    if type_filter or category_filter:
        primary = [
            product
            for product in products
            if (
                not type_filter
                or (product.category_type or "").lower() in type_filter
                or (product.category or "").lower() in category_filter
            )
        ]
        if primary:
            products = primary

    _, _, tfidf = build_similarity_matrix()
    semantic_scores = {product.id: 0.0 for product in products}
    query_text = " ".join(
        [
            prompt or "",
            plan.style_direction or "",
            plan.occasion or "",
            plan.formality or "",
            " ".join(plan.preferred_category_types),
            " ".join(plan.must_have_categories),
            " ".join(plan.preferred_colors),
            " ".join(plan.fit_strategy),
        ]
    ).strip()

    if query_text and tfidf is not None:
        try:
            query_vector = tfidf.transform([query_text])
            product_matrix = tfidf.transform([product_search_text(product) for product in products])
            sims = np.array(cosine_similarity(query_vector, product_matrix).flatten())
            semantic_scores = {
                product.id: float(score) for product, score in zip(products, sims)
            }
        except Exception:
            semantic_scores = {product.id: 0.0 for product in products}

    products = sorted(
        products,
        key=lambda product: (
            semantic_scores.get(product.id, 0.0),
            product.rating or 0.0,
        ),
        reverse=True,
    )
    return products[:max_candidates], semantic_scores

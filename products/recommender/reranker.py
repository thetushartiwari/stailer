from __future__ import annotations

import json
import logging
import os

import requests
from django.conf import settings

from products.models import Product, UserProfile

from .schemas import CandidateScore, RerankChoice, StylePlan

logger = logging.getLogger(__name__)


def _candidate_payload(product: Product, score: CandidateScore) -> dict:
    return {
        "id": product.id,
        "title": product.title,
        "brand": product.brand,
        "gender": product.gender,
        "category": product.category,
        "category_type": product.category_type,
        "colors": product.colors,
        "fit": product.fit,
        "style_tags": product.style_tags,
        "price": product.price,
        "rating": product.rating,
        "description": product.description[:300],
        "product_url": product.product_url,
        "ml_score": round(score.total, 4),
        "score_components": {
            "semantic": round(score.semantic, 4),
            "metadata": round(score.metadata, 4),
            "body_fit": round(score.body_fit, 4),
            "skin_color": round(score.skin_color, 4),
            "feedback": round(score.feedback, 4),
            "quality": round(score.quality, 4),
        },
    }


def _local_rerank(
    products: list[Product],
    scores: dict[int, CandidateScore],
    max_results: int,
    min_score: float,
) -> tuple[list[RerankChoice], list[dict]]:
    selected = []
    rejected = []
    for product in sorted(products, key=lambda item: scores[item.id].total, reverse=True):
        score = scores[product.id]
        confidence = min(max(score.total + 0.35, 0.0), 0.95)
        if score.total < min_score:
            rejected.append({"id": product.id, "reason": "Below relevance threshold"})
            continue
        selected.append(
            RerankChoice(
                product_id=product.id,
                confidence=confidence,
                reason="; ".join(score.reasons[:3]) or "Best available catalog match",
            )
        )
        if len(selected) >= max_results:
            break
    return selected, rejected


def rerank_candidates(
    plan: StylePlan,
    profile: UserProfile | None,
    prompt: str,
    products: list[Product],
    scores: dict[int, CandidateScore],
    max_results: int = 12,
) -> tuple[list[RerankChoice], list[dict]]:
    if not products:
        return [], []

    products = sorted(products, key=lambda item: scores[item.id].total, reverse=True)[:40]
    min_score = 0.18 if prompt else 0.0
    return _local_rerank(products, scores, max_results, min_score)

from __future__ import annotations

from products.models import Product

from .schemas import CandidateScore, RerankChoice


def build_explanations(product: Product, score: CandidateScore, choice: RerankChoice | None) -> list[str]:
    explanations = []
    if choice and choice.reason:
        explanations.append(choice.reason)
    explanations.extend(score.reasons)
    if score.semantic > 0.12:
        explanations.append(f"Request match {int(score.semantic * 100)}%")
    if score.total > 0:
        explanations.append(f"Compatibility score {int(min(score.total + 0.35, 0.95) * 100)}%")
    return list(dict.fromkeys(explanations))[:3]

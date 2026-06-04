from __future__ import annotations

from products.models import Product

from .schemas import CandidateScore, RerankChoice


def build_explanations(product: Product, score: CandidateScore, choice: RerankChoice | None) -> list[str]:
    explanations = []
    if choice and choice.reason and ";" not in choice.reason:
        explanations.append(choice.reason)
    explanations.extend(score.reasons)
    if score.semantic > 0.12:
        explanations.append(f"Request match {int(score.semantic * 100)}%")
    if score.total > 0:
        explanations.append(f"Compatibility score {int(min(score.total + 0.35, 0.95) * 100)}%")
    unique_exps = list(dict.fromkeys(explanations))

    # Prioritize biometric and personalization feedback over generic query matching tags
    def score_priority(exp: str) -> int:
        exp_lower = exp.lower()
        if "body dna" in exp_lower or "skin dna" in exp_lower:
            return 0  # Highest priority
        if "proportions" in exp_lower or "height" in exp_lower or "stature" in exp_lower:
            return 1  # High priority
        if "feedback" in exp_lower or "preference" in exp_lower:
            return 2
        if "matches planned" in exp_lower or "styling context" in exp_lower:
            return 3
        if "semantically matches" in exp_lower or "request match" in exp_lower:
            return 4
        return 5  # Lower priority

    unique_exps.sort(key=score_priority)
    return unique_exps[:3]

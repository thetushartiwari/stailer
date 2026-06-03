from dataclasses import dataclass, field
from typing import Any


@dataclass
class StylePlan:
    audience: str = "all"
    occasion: str = ""
    formality: str = ""
    must_have_categories: list[str] = field(default_factory=list)
    preferred_category_types: list[str] = field(default_factory=list)
    avoid_categories: list[str] = field(default_factory=list)
    preferred_colors: list[str] = field(default_factory=list)
    fit_strategy: list[str] = field(default_factory=list)
    style_direction: str = ""
    budget_max: float | None = None
    minimum_confidence: float = 0.55
    stylist_response: str = ""
    source: str = "local"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StylePlan":
        data = data or {}
        budget = data.get("budget_max")
        try:
            budget = float(budget) if budget not in ("", None) else None
        except (TypeError, ValueError):
            budget = None

        def as_list(value: Any) -> list[str]:
            if value is None:
                return []
            if isinstance(value, list):
                return [str(item).strip() for item in value if str(item).strip()]
            return [str(value).strip()] if str(value).strip() else []

        return cls(
            audience=str(data.get("audience") or data.get("target_gender") or "all").lower(),
            occasion=str(data.get("occasion") or "").lower(),
            formality=str(data.get("formality") or "").lower(),
            must_have_categories=as_list(data.get("must_have_categories") or data.get("preferred_categories")),
            preferred_category_types=as_list(data.get("preferred_category_types")),
            avoid_categories=as_list(data.get("avoid_categories") or data.get("excluded_categories")),
            preferred_colors=[item.lower() for item in as_list(data.get("preferred_colors") or data.get("colors"))],
            fit_strategy=[item.lower() for item in as_list(data.get("fit_strategy"))],
            style_direction=str(data.get("style_direction") or data.get("intent_summary") or ""),
            budget_max=budget,
            minimum_confidence=float(data.get("minimum_confidence") or 0.55),
            stylist_response=str(data.get("stylist_response") or ""),
            source=str(data.get("source") or "local"),
        )


@dataclass
class CandidateScore:
    product_id: int
    semantic: float = 0.0
    skin_color: float = 0.0
    body_fit: float = 0.0
    feedback: float = 0.0
    quality: float = 0.0
    metadata: float = 0.0
    total: float = 0.0
    reasons: list[str] = field(default_factory=list)


@dataclass
class RerankChoice:
    product_id: int
    confidence: float
    reason: str


@dataclass
class RecommendationResult:
    products: list[Any]
    plan: StylePlan
    explanations: dict[int, list[str]]
    scores: dict[int, CandidateScore]
    rejected: list[dict[str, Any]] = field(default_factory=list)
    stylist_response: str = ""

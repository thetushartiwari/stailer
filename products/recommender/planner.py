from __future__ import annotations

import json
import os
import re
import logging

import requests
from django.conf import settings

from products.models import Product, UserProfile
from products.recommendation_model import COLOR_KEYWORDS

from .schemas import StylePlan
from .validator import normalize_audience

logger = logging.getLogger(__name__)


GENDER_BY_PROMPT = {
    "men": ("men", "mens", "male", "man"),
    "women": ("women", "womens", "female", "woman", "ladies"),
    "kids": ("kids", "kid", "boys", "boy", "girls", "girl", "infant", "junior"),
}

SYNONYMS = {
    "wedding": "Traditional",
    "marriage": "Traditional",
    "office": "Formal",
    "work": "Formal",
    "interview": "Formal",
    "gym": "Sportswear",
    "sports": "Sportswear",
    "running": "Sportswear",
    "activewear": "Sportswear",
    "festive": "Ethnic",
    "holiday": "Casual",
    "daily": "Casual",
    "lounge": "Casual",
    "nightwear": "Casual",
    "sleepwear": "Casual",
}

CAT_SYNONYMS = {
    "tee": "tshirt",
    "t-shirt": "tshirt",
    "tshirts": "tshirt",
    "denim": "jeans",
    "denims": "jeans",
    "kurti": "kurta",
    "kurtas": "kurta",
    "blazer": "suit",
    "suit": "trousers",
    "pant": "trousers",
    "pants": "trousers",
    "chinos": "trousers",
    "top": "shirt",
    "crop": "top",
}


def build_catalog_metadata(selected_gender: str = "all") -> dict:
    audience = normalize_audience(selected_gender)
    qs = Product.objects.all()
    if audience in {"men", "women", "kids"}:
        qs = qs.filter(gender=audience)

    prices = [price for price in qs.values_list("price", flat=True) if price is not None]
    category_type_by_category: dict[str, set[str]] = {}
    for category, category_type in qs.values_list("category", "category_type"):
        if category and category_type:
            category_type_by_category.setdefault(category, set()).add(category_type)

    return {
        "selected_gender": audience,
        "available_genders": sorted({g for g in Product.objects.values_list("gender", flat=True) if g}),
        "available_category_types": sorted({c for c in qs.values_list("category_type", flat=True) if c}),
        "available_categories": sorted({c for c in qs.values_list("category", flat=True) if c}),
        "category_type_by_category": {
            category: sorted(values) for category, values in category_type_by_category.items()
        },
        "price_range": [min(prices), max(prices)] if prices else [0, 0],
    }


def profile_payload(profile: UserProfile | None, selected_gender: str) -> dict:
    if not profile:
        return {"selected_gender": selected_gender}
    return {
        "name": profile.user_name or "",
        "age": profile.age,
        "selected_gender": selected_gender,
        "skin_tone": profile.skin_tone or "",
        "body_type": profile.body_type or "",
        "bmi_category": getattr(profile, "bmi_category", "Normal") or "Normal",
        "height_cm": profile.height,
        "weight_kg": profile.weight,
        "bust": profile.bust_size,
        "waist": profile.waist_size,
        "hips": profile.hips_size,
    }


def _extract_budget(prompt: str) -> float | None:
    match = re.search(r"(?:under|below|less than|upto|up to)\s*(?:rs\.?|inr|₹)?\s*(\d+)\s*(k)?", prompt)
    if not match:
        return None
    value = float(match.group(1))
    if match.group(2) or value < 100:
        value *= 1000
    return value


def _local_plan(prompt: str, profile: UserProfile | None, selected_gender: str, metadata: dict) -> StylePlan:
    prompt_lower = (prompt or "").lower()
    prompt_words = set(re.findall(r'[a-z0-9]+', prompt_lower))
    audience = normalize_audience(selected_gender)
    for candidate, terms in GENDER_BY_PROMPT.items():
        if any(term in prompt_words for term in terms):
            audience = candidate
            break
    if audience == "all" and getattr(profile, "age", None) is not None and profile.age < 16:
        audience = "kids"

    preferred_types = []
    for ct in metadata.get("available_category_types", []):
        ct_lower = ct.lower()
        ct_words = set(re.findall(r'[a-z0-9]+', ct_lower))
        if (ct_lower in prompt_lower) or bool(ct_words & prompt_words):
            preferred_types.append(ct)
            continue
        for syn, mapped_ct in SYNONYMS.items():
            if syn in prompt_words and mapped_ct.lower() == ct_lower:
                preferred_types.append(ct)
                break

    categories = []
    category_type_by_category = metadata.get("category_type_by_category", {})
    resolved_prompt_words = set(prompt_words)
    for w in prompt_words:
        if w in CAT_SYNONYMS:
            resolved_prompt_words.add(CAT_SYNONYMS[w])

    for category in metadata.get("available_categories", []):
        category_lower = category.lower()
        cat_words = set(re.findall(r'[a-z0-9]+', category_lower))
        cat_words = cat_words - {"mens", "womens", "kids", "men", "women", "boys", "girls", "junior", "child"}
        
        category_matches_prompt = bool(cat_words & resolved_prompt_words)
        type_matches_prompt = bool(set(preferred_types) & set(category_type_by_category.get(category, [])))
        if category_matches_prompt or type_matches_prompt:
            categories.append(category)

    colors = sorted({color for color in COLOR_KEYWORDS if color in prompt_words})
    occasion = next((term for term in ["office", "wedding", "party", "gym", "college", "festive"] if term in prompt_words), "")
    formality = "formal" if "Formal" in preferred_types else ""

    name = getattr(profile, "user_name", None)
    greeting = f"{name}, " if name else ""
    response = (
        f"{greeting}I built a catalog-backed styling plan from your prompt and diagnostic profile. "
        "I will only keep products that pass audience and relevance checks."
    )

    return StylePlan(
        audience=audience,
        occasion=occasion,
        formality=formality,
        must_have_categories=categories[:8],
        preferred_category_types=preferred_types,
        avoid_categories=[],
        preferred_colors=colors,
        fit_strategy=[],
        style_direction=prompt,
        budget_max=_extract_budget(prompt_lower),
        minimum_confidence=0.55 if prompt else 0.4,
        stylist_response=response,
        source="local_planner",
    )


def _normalize_to_catalog(plan: StylePlan, metadata: dict) -> StylePlan:
    available_genders = set(metadata.get("available_genders", []))
    if plan.audience not in available_genders and plan.audience != "all":
        plan.audience = metadata.get("selected_gender", "all")

    available_types = set(metadata.get("available_category_types", []))
    available_categories = set(metadata.get("available_categories", []))
    category_type_by_category = metadata.get("category_type_by_category", {})

    plan.preferred_category_types = [
        item for item in plan.preferred_category_types if item in available_types
    ]
    plan.must_have_categories = [
        item for item in plan.must_have_categories if item in available_categories
    ]
    if plan.preferred_category_types and plan.must_have_categories:
        wanted_types = set(plan.preferred_category_types)
        plan.must_have_categories = [
            category
            for category in plan.must_have_categories
            if wanted_types & set(category_type_by_category.get(category, []))
        ]
    plan.avoid_categories = [item for item in plan.avoid_categories if item in available_categories]
    plan.preferred_colors = [item for item in plan.preferred_colors if item in COLOR_KEYWORDS]
    plan.minimum_confidence = max(0.0, min(0.95, plan.minimum_confidence))
    return plan


def create_style_plan(prompt: str, profile: UserProfile | None, selected_gender: str = "all") -> StylePlan:
    selected_gender = normalize_audience(selected_gender)
    metadata = build_catalog_metadata(selected_gender)
    gemini_key = getattr(settings, "GEMINI_API_KEY", None) or os.environ.get("GEMINI_API_KEY")

    if gemini_key and prompt:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={gemini_key}"
            instruction = (
                "You are stAiler's AI stylist planner. Given a user profile and styling prompt, "
                "produce a concise catalog-backed style plan. Use ONLY category values from catalog_metadata. "
                "Keep stylist_response under 100 characters. Keep style_direction under 80 characters. "
                "budget_max should be null unless a budget is explicitly mentioned. "
                "Use the user's skin_tone to add harmonious colors to preferred_colors. "
                "Use their body_type, bmi_category, and height_cm to determine fit_strategy array values (e.g. ['oversized', 'slim', 'draped']). "
                "If the user mentions their own skin tone, body shape, or height directly in the prompt text, "
                "honour those signals in fit_strategy and preferred_colors even if the stored profile fields are empty."
            )
            # Trim metadata to reduce payload size
            trimmed_metadata = {
                "selected_gender": metadata["selected_gender"],
                "available_genders": metadata["available_genders"],
                "available_category_types": metadata["available_category_types"],
                "available_categories": metadata["available_categories"][:40],
                "price_range": metadata["price_range"],
            }
            payload = {
                "user_profile": profile_payload(profile, selected_gender),
                "prompt": prompt,
                "catalog_metadata": trimmed_metadata,
            }
            # Use responseSchema to force structured output and prevent hallucinated text
            response_schema = {
                "type": "OBJECT",
                "properties": {
                    "audience": {"type": "STRING"},
                    "occasion": {"type": "STRING"},
                    "formality": {"type": "STRING"},
                    "must_have_categories": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "preferred_category_types": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "avoid_categories": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "preferred_colors": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "fit_strategy": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "style_direction": {"type": "STRING"},
                    "minimum_confidence": {"type": "NUMBER"},
                    "stylist_response": {"type": "STRING"},
                },
                "required": ["audience", "must_have_categories", "preferred_category_types", "stylist_response"],
            }
            session = requests.Session()
            result = session.post(
                url,
                json={
                    "contents": [{"parts": [{"text": json.dumps(payload)}]}],
                    "systemInstruction": {"parts": [{"text": instruction}]},
                    "safetySettings": [
                        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                    ],
                    "generationConfig": {
                        "responseMimeType": "application/json",
                        "responseSchema": response_schema,
                        "maxOutputTokens": 2048,
                    },
                },
                headers={"Content-Type": "application/json"},
                timeout=15,
            )
            if result.status_code == 200:
                text = result.json()["candidates"][0]["content"]["parts"][0]["text"]
                try:
                    plan = StylePlan.from_dict(json.loads(text))
                    plan.source = "gemini_planner"
                    return _normalize_to_catalog(plan, metadata)
                except json.JSONDecodeError as jde:
                    logger.warning("Gemini planner JSON parse failed: %s", jde)
            else:
                logger.warning("Gemini planner returned HTTP %s: %s", result.status_code, result.text[:400])
        except Exception as exc:
            logger.warning("Gemini planner failed: %s", exc)

    return _normalize_to_catalog(_local_plan(prompt, profile, selected_gender, metadata), metadata)


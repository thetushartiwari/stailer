"""
products/recommender/biometric_extractor.py

Natural Language Biometric Extraction
--------------------------------------
Parses free-text prompts for biometric signals:
  - Height (feet/inches, cm)
  - Body type / silhouette
  - Skin tone / undertone
  - Weight (kg, lbs)

Returns a dict with only the keys it was able to extract.
Callers are responsible for deciding whether to apply extracted values
(non-destructive by design).
"""
from __future__ import annotations

import json
import logging
import os
import re

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# ── Skin Tone Mapping ────────────────────────────────────────────────────────
# Canonical values must match what UserProfile.skin_tone stores ("Fair", "Medium", etc.)

_SKIN_TONE_KEYWORDS: dict[str, list[str]] = {
    "Fair": [
        "fair", "light skin", "light complexion", "fair complexion",
        "fair skin", "pale", "pale skin", "light toned", "porcelain",
    ],
    "Medium": [
        "medium", "medium skin", "medium tone", "medium complexion",
        "wheatish", "wheatish complexion", "tan", "tanned skin",
        "warm skin", "warm tone",
    ],
    "Olive": [
        "olive", "olive skin", "olive tone", "olive complexion",
        "dusky", "dusky skin", "dusky complexion", "brown skin",
        "brown complexion", "brownish",
    ],
    "Deep": [
        "deep", "deep skin", "deep complexion", "dark skin",
        "dark complexion", "dark tone", "rich skin", "rich complexion",
        "ebony",
    ],
}

# ── Body Type Mapping ────────────────────────────────────────────────────────
# Canonical values must match what UserProfile.body_type / wizard chips store.

_BODY_TYPE_KEYWORDS: dict[str, list[str]] = {
    # Women
    "Hourglass": [
        "hourglass", "curvy", "curves", "curvy figure", "curvaceous",
        "hourglass figure", "hourglass shape", "hourglass body",
    ],
    "Pear": [
        "pear", "pear shaped", "pear shape", "pear body", "triangle body",
        "bottom heavy", "pear figure",
    ],
    "Apple": [
        "apple", "apple shaped", "apple shape", "round body", "round belly",
        "midsection weight",
    ],
    "Inverted Triangle": [
        "inverted triangle", "inverted triangular", "broad shoulders",
        "narrow hips broad shoulders",
    ],
    # Men
    "V-Taper": [
        "v-taper", "v taper", "v shape", "v shaped", "athletic v",
        "broad shoulders narrow waist",
    ],
    "Trapezoid": [
        "trapezoid", "trapezoidal", "rectangular athletic",
    ],
    "Triangle": [
        "triangle", "triangular body", "pear shaped men", "bottom heavy men",
    ],
    "Oval": [
        "oval", "round shape men", "oval body",
    ],
    # Shared / gender-neutral
    "Rectangle": [
        "rectangle", "rectangular", "straight body", "straight figure",
        "straight build", "athletic build", "athletic frame",
        "slim straight", "lean build",
    ],
    "Athletic": [
        "athletic", "fit body", "muscular", "toned", "toned body",
        "sporty body", "fit build",
    ],
    "Round": [
        "round", "chubby", "plus size", "full figured", "full figure",
        "big boned",
    ],
    "Petite": [
        "petite", "petite frame", "slim", "slender", "thin build",
        "lean", "skinny",
    ],
}

# ── Height conversion helpers ────────────────────────────────────────────────

def _feet_inches_to_cm(feet: float, inches: float = 0.0) -> float:
    return round((feet * 30.48) + (inches * 2.54), 2)


def _extract_height(text: str) -> float | None:
    """
    Detect height expressions and return cm float.
    Handles: 5'8, 5'8", 5 feet 8, 5ft 8in, 5 ft 8, 172cm, 172 cm, 1.72m
    """
    # Apostrophe shorthand: 5'8 or 5'8"
    m = re.search(r"(\d)\s*['\u2019]\s*(\d{1,2})\s*\"?", text)
    if m:
        return _feet_inches_to_cm(int(m.group(1)), int(m.group(2)))

    # Feet-only shorthand: 5'
    m = re.search(r"(\d)\s*['\u2019](?!\s*\d)", text)
    if m:
        return _feet_inches_to_cm(int(m.group(1)))

    # Verbose: "5 feet 8 inches", "5 ft 8 in", "5 feet 8"
    m = re.search(
        r"(\d)\s*(?:feet|foot|ft)\s*(\d{1,2})\s*(?:inches?|in\.?|\")?",
        text,
    )
    if m:
        return _feet_inches_to_cm(int(m.group(1)), int(m.group(2)))

    # Feet only: "5 feet", "5 ft"
    m = re.search(r"(\d)\s*(?:feet|foot|ft)\b", text)
    if m:
        return _feet_inches_to_cm(int(m.group(1)))

    # Centimetres: 172cm, 172 cm
    m = re.search(r"(\d{2,3})\s*cm\b", text)
    if m:
        val = float(m.group(1))
        if 50.0 <= val <= 250.0:
            return val

    # Metres: 1.72m, 1.65 m
    m = re.search(r"(1\.\d{1,2})\s*m\b", text)
    if m:
        val = float(m.group(1)) * 100
        if 50.0 <= val <= 250.0:
            return round(val, 2)

    return None


def _extract_weight(text: str) -> float | None:
    """
    Detect weight expressions and return kg float.
    Handles: 60kg, 60 kg, 60 kilos, 132lbs, 132 lbs
    """
    # Kilograms
    m = re.search(r"(\d{2,3})\s*(?:kg|kilos?|kilograms?)\b", text)
    if m:
        val = float(m.group(1))
        if 10.0 <= val <= 300.0:
            return val

    # Pounds -> kg
    m = re.search(r"(\d{2,3})\s*(?:lbs?|pounds?)\b", text)
    if m:
        val = round(float(m.group(1)) * 0.453592, 1)
        if 10.0 <= val <= 300.0:
            return val

    return None


def _extract_skin_tone(text: str) -> str | None:
    for canonical, keywords in _SKIN_TONE_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return canonical
    return None


def _extract_body_type_regex(text: str) -> str | None:
    for canonical, keywords in _BODY_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return canonical
    return None


def _extract_body_type_gemini(prompt: str) -> str | None:
    """
    Fallback: ask Gemini to classify body type from ambiguous natural language.
    Returns None silently on any failure.
    """
    gemini_key = getattr(settings, "GEMINI_API_KEY", None) or os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        return None

    valid_types = list(_BODY_TYPE_KEYWORDS.keys())
    instruction = (
        "You are a body type classifier. Given a sentence, extract ONLY the body type "
        f"mentioned by the user. Return EXACTLY one of these values: {valid_types}. "
        "If no body type is mentioned return the string 'none'. No other text."
    )
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}"
        result = requests.post(
            url,
            json={
                "contents": [{"parts": [{"text": f"Sentence: {prompt}"}]}],
                "systemInstruction": {"parts": [{"text": instruction}]},
                "generationConfig": {"maxOutputTokens": 20, "temperature": 0.0},
            },
            headers={"Content-Type": "application/json"},
            timeout=5,
        )
        if result.status_code == 200:
            raw = result.json()["candidates"][0]["content"]["parts"][0]["text"].strip().strip('"')
            if raw in valid_types:
                return raw
    except Exception as exc:
        logger.debug("Gemini body type extraction failed silently: %s", exc)
    return None


# ── Public API ───────────────────────────────────────────────────────────────

def extract_biometrics_from_text(prompt: str) -> dict:
    """
    Parse a free-text prompt for biometric signals.

    Returns a dict containing any of:
        height_cm  (float)
        weight_kg  (float)
        skin_tone  (str: "Fair" | "Medium" | "Olive" | "Deep")
        body_type  (str: e.g. "Hourglass", "V-Taper", etc.)

    Only keys that were successfully extracted are present.
    This function never raises — all errors are logged and silently ignored.
    """
    if not prompt or not isinstance(prompt, str):
        return {}

    text = prompt.lower().strip()
    result: dict = {}

    try:
        height = _extract_height(text)
        if height is not None:
            result["height_cm"] = height
    except Exception:
        pass

    try:
        weight = _extract_weight(text)
        if weight is not None:
            result["weight_kg"] = weight
    except Exception:
        pass

    try:
        skin = _extract_skin_tone(text)
        if skin:
            result["skin_tone"] = skin
    except Exception:
        pass

    try:
        body = _extract_body_type_regex(text)
        if body:
            result["body_type"] = body
        # Gemini fallback only if regex found nothing
        # (uncomment the block below to enable — adds ~1-2s latency)
        # elif prompt:
        #     body = _extract_body_type_gemini(prompt)
        #     if body:
        #         result["body_type"] = body
    except Exception:
        pass

    if result:
        logger.debug("Biometric extraction from prompt: %s", result)

    return result

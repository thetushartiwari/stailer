# products/stylist_engine.py
import re
import os
import json
import pickle
import logging
import requests
import numpy as np
from django.conf import settings
from sklearn.metrics.pairwise import cosine_similarity
from .models import Product, UserPreference
from .recommendation_model import build_similarity_matrix, get_color_similarity, COLOR_KEYWORDS


logger = logging.getLogger(__name__)

# Curated stylist color mapping based on skin tones
SKIN_TONE_COLORS = {
    "fair": ["silver", "lavender", "emerald green", "pastel blue", "deep berry", "black", "soft gray", "white", "pink", "cherry"],
    "medium": ["mustard", "gold", "olive green", "cream", "tan", "rust red", "teal", "navy blue", "beige", "brown"],
    "olive": ["peach", "beige", "olive green", "gold", "burgundy", "charcoal", "white", "tan", "brown", "navy", "cream"],
    "deep": ["crimson red", "gold", "royal blue", "white", "mustard", "emerald green", "deep purple", "black", "orange", "yellow"]
}

VIBE_KEYWORDS = {
    "minimalist": ["minimalist", "solid", "plain", "clean", "simple", "van heusen", "monochrome"],
    "streetwear": ["streetwear", "oversized", "graphic", "printed", "hoodie", "puffer", "rebelroarr", "cargo", "joggers"],
    "traditional": ["traditional", "ethnic", "kurta", "nehru", "woven", "embroidered", "indie", "saree", "sherwani", "lehenga", "anarkali"],
    "athleisure": ["athleisure", "sporty", "outdoor", "windcheater", "activewear", "dri-fit", "trackpant"],
    "chic": ["chic", "elegant", "midi", "maxi", "flare", "puff sleeve", "sweetheart", "jumpsuit"]
}

FIT_KEYWORDS = {
    "oversized": ["oversized", "plus size", "loose", "relaxed", "drop-shoulder", "baggy"],
    "slim": ["slim fit", "slim", "tight", "tailored", "bodycon"],
    "regular": ["regular", "comfortable", "classic", "standard", "straight"]
}

# Paths to ML artifacts
ML_DIR = os.path.join(os.path.dirname(__file__), "ml_artifacts")
SKIN_CLASSIFIER_PATH = os.path.join(ML_DIR, "skin_classifier.pkl")
BODY_CLASSIFIER_PATH = os.path.join(ML_DIR, "body_classifier.pkl")

def get_loaded_classifier(path):
    if os.path.exists(path):
        try:
            with open(path, "rb") as f:
                return pickle.load(f)
        except Exception:
            return None
    return None

def classify_gender(title, description, product_url=""):
    """Categorize product as men, women, or unisex dynamically using keywords and URL patterns."""
    text = f"{title} {description} {product_url}".lower()
    
    if "unisex" in text:
        return "unisex"

    # Strip "women" and "woman" before checking for "men" to prevent false masculine matching
    text_no_women = text.replace("women", "").replace("woman", "")
    
    is_women = any(kw in text for kw in ["women", "girl", "female", "dress", "saree", "kurti", "lehenga", "gown", "midi", "flare", "kalini", "athena", "anouk female", "womens_"])
    is_men = any(kw in text_no_women for kw in ["men", "boy", "male", "polo", "short kurta", "tshirt", "tee", "shirt", "pants", "trouser", "mens_"])
    
    if not is_women and not is_men and product_url:
        if "-women" in product_url or "/women" in product_url:
            is_women = True
        elif "-men" in product_url or "/men" in product_url:
            is_men = True
            
    if is_women:
        return "women"
    elif is_men:
        return "men"
    else:
        return "unisex"







def predict_skin_tone_from_rgb(rgb_list):
    """Computer Vision Supervised KNN Classifier Pipeline."""
    classifier = get_loaded_classifier(SKIN_CLASSIFIER_PATH)
    if classifier is None:
        # Fallback to absolute RGB coordinates heuristic
        r, g, b = rgb_list[0], rgb_list[1], rgb_list[2]
        if r > 230: return "Fair"
        if r > 180: return "Medium"
        if r > 120: return "Olive"
        return "Deep"
        
    features = np.array([rgb_list])
    pred_idx = int(classifier.predict(features)[0])
    mapping = {0: "Fair", 1: "Medium", 2: "Olive", 3: "Deep"}
    return mapping.get(pred_idx, "Medium")

def predict_body_shape(height_cm, weight_kg, bust_in, waist_in, hips_in):
    """Biometric Supervised Logistic Regression Classifier Pipeline."""
    classifier = get_loaded_classifier(BODY_CLASSIFIER_PATH)
    
    # Calculate anthropometric ratios
    bust_waist = bust_in / waist_in if waist_in else 1.0
    hips_waist = hips_in / waist_in if waist_in else 1.0
    bust_hips = bust_in / hips_in if hips_in else 1.0
    bmi = weight_kg / ((height_cm / 100.0) ** 2) if height_cm else 22.0

    features = np.array([[bust_waist, hips_waist, bust_hips, bmi]])

    if bmi < 18.5:
        return "Petite"

    if classifier is None:
        # Wharton Heuristics Fallback
        if bust_waist >= 1.25 and hips_waist >= 1.25 and abs(bust_hips - 1.0) <= 0.06:
            return "Hourglass"
        if bmi >= 27.5:
            return "Round"
        if bust_hips >= 1.12:
            return "Athletic"
        if bmi < 18.5:
            return "Petite"
        return "Rectangle"

    pred_idx = int(classifier.predict(features)[0])
    mapping = {0: "Hourglass", 1: "Round", 2: "Rectangle", 3: "Athletic", 4: "Petite"}
    return mapping.get(pred_idx, "Rectangle")



def update_preferences(profile, product, action):
    """Dynamic Statistical Gradient-Drift Self-Learning Algorithm."""
    if not profile:
        return
        
    filters = profile.personalization_filters or {}
    style_affinity = filters.setdefault("style_affinity", {k: 0.5 for k in VIBE_KEYWORDS.keys()})
    preferred_fits = filters.setdefault("preferred_fits", {k: 0.5 for k in FIT_KEYWORDS.keys()})
    preferred_colors = filters.setdefault("preferred_colors", {})
    preferred_brands = filters.setdefault("preferred_brands", [])
    
    prod_text = (product.title + " " + product.description).lower()
    
    # Gradient learning step coefficients (likes pull vector close, dislikes push far away)
    step = 0.08 if action == "like" else -0.15
    
    for vibe, keywords in VIBE_KEYWORDS.items():
        if any(kw in prod_text for kw in keywords):
            style_affinity[vibe] = round(max(0.0, min(1.0, style_affinity[vibe] + step)), 2)
            
    for fit, keywords in FIT_KEYWORDS.items():
        if any(kw in prod_text for kw in keywords):
            preferred_fits[fit] = round(max(0.0, min(1.0, preferred_fits[fit] + step)), 2)
            
    for color in COLOR_KEYWORDS:
        if color in prod_text:
            score = preferred_colors.get(color, 0.5)
            preferred_colors[color] = round(max(0.0, min(1.0, score + step)), 2)
            
    brand = product.brand.strip() if getattr(product, 'brand', None) else product.title.split()[0]
    if action == "like":
        if brand not in preferred_brands:
            preferred_brands.append(brand)
    else:
        if brand in preferred_brands:
            preferred_brands.remove(brand)

    profile.personalization_filters = filters
    profile.save()



def rank_products(profile, intent, prompt_query="", gender_filter="all", top_n=12):
    from .recommender.service import recommend_for_profile

    result = recommend_for_profile(
        profile=profile,
        prompt=prompt_query or (intent or {}).get("intent_summary", ""),
        selected_gender=gender_filter,
        max_results=top_n,
    )
    return result.products



import re


COLOR_KEYWORDS = {
    "red", "blue", "green", "yellow", "black", "white", "grey", "gray", "brown",
    "pink", "purple", "orange", "beige", "navy", "maroon", "cream", "tan",
    "olive", "teal", "coral", "gold", "silver", "mustard", "cherry",
}

FIT_KEYWORDS = {
    "oversized": ["oversized", "loose", "relaxed", "drop-shoulder", "baggy"],
    "slim": ["slim fit", "slim", "tight", "tailored", "bodycon", "fitted"],
    "regular": ["regular", "comfortable", "classic", "standard", "straight"],
}

STYLE_KEYWORDS = {
    "traditional": [
        "traditional", "ethnic", "sherwani", "saree", "lehenga", "kurta",
        "nehru", "woven", "embroidered", "anarkali", "sharara", "pathani",
        "dupatta", "salwar",
    ],
    "streetwear": ["streetwear", "graphic", "printed", "hoodie", "puffer", "cargo", "sweatshirt"],
    "athleisure": ["athleisure", "sporty", "activewear", "trackpant", "joggers", "workout", "sports", "running", "gym"],
    "chic": ["chic", "elegant", "midi", "maxi", "flare", "puff sleeve", "jumpsuit", "coord"],
    "minimalist": ["minimalist", "solid", "plain", "clean", "simple", "monochrome"],
}

WOMEN_SIGNALS = [
    "women", "womens", "woman", "female", "ladies",
    "saree", "lehenga", "dupatta", "blouse", "palazzo", "anarkali",
    "sharara", "kurti", "gown", "dress", "crop top",
]

MEN_SIGNALS = [
    "men", "mens", "man", "male",
]

KIDS_SIGNALS = ["kids", "kid", "boys", "boy", "girls", "girl", "infant", "junior"]

EXPLICIT_WOMEN_SIGNALS = ["women", "womens", "woman", "female", "ladies"]
EXPLICIT_MEN_SIGNALS = ["men", "mens", "man", "male"]
EXPLICIT_KIDS_SIGNALS = KIDS_SIGNALS

MEN_CATEGORY_BY_TOKEN = {
    "formal shirt": "mens_formal_shirt",
    "track pant": "mens_trackpant",
    "trackpant": "mens_trackpant",
    "t-shirt": "mens_tshirt",
    "tshirt": "mens_tshirt",
    "sherwani": "mens_sherwani",
    "pathani": "mens_pathani_suit",
    "nehru": "mens_nehru_jacket",
    "trousers": "mens_trousers",
    "trouser": "mens_trousers",
    "chinos": "mens_chinos",
    "joggers": "mens_joggers",
    "jogger": "mens_joggers",
    "sweatshirt": "mens_sweatshirt",
    "hoodie": "mens_hoodie",
    "shorts": "mens_shorts",
    "blazer": "mens_blazer",
    "jacket": "mens_jacket",
    "jeans": "mens_jeans",
    "polo": "mens_polo",
    "shirt": "mens_shirt",
    "suit": "mens_suit",
    "kurta": "mens_kurta_pajama",
}

WOMEN_CATEGORY_BY_TOKEN = {
    "saree blouse": "womens_saree_blouse",
    "party dress": "womens_party_dress",
    "crop top": "womens_top",
    "co-ord": "womens_coord",
    "coord": "womens_coord",
    "saree": "womens_sarees",
    "lehenga": "womens_lehenga",
    "anarkali": "womens_anarkali",
    "sharara": "womens_sharara",
    "palazzo": "womens_palazzo",
    "jumpsuit": "womens_jumpsuit",
    "blouse": "womens_blouse",
    "midi": "womens_midi_dress",
    "maxi": "womens_maxi_dress",
    "dress": "womens_midi_dress",
    "top": "womens_top",
    "kurta": "womens_anarkali",
}

KIDS_CATEGORY_BY_TOKEN = {
    "formal shirt": "kids_formal_shirt",
    "track pant": "kids_trackpant",
    "trackpant": "kids_trackpant",
    "t-shirt": "kids_tshirt",
    "tshirt": "kids_tshirt",
    "sherwani": "kids_sherwani",
    "pathani": "kids_pathani_suit",
    "nehru": "kids_nehru_jacket",
    "trousers": "kids_trousers",
    "trouser": "kids_trousers",
    "chinos": "kids_chinos",
    "joggers": "kids_joggers",
    "jogger": "kids_joggers",
    "sweatshirt": "kids_sweatshirt",
    "hoodie": "kids_hoodie",
    "shorts": "kids_shorts",
    "blazer": "kids_blazer",
    "jacket": "kids_jacket",
    "jeans": "kids_jeans",
    "polo": "kids_polo",
    "shirt": "kids_shirt",
    "suit": "kids_suit",
    "kurta": "kids_kurta_pajama",
}

FORMAL_CATEGORY_TOKENS = {
    "mens_formal_shirt", "mens_blazer", "mens_trousers", "mens_suit", "mens_chinos",
    "womens_shirt", "womens_trousers", "womens_jacket",
    "kids_formal_shirt", "kids_blazer", "kids_trousers", "kids_suit", "kids_chinos",
}

SPORTS_CATEGORY_TOKENS = {
    "mens_trackpant", "mens_joggers", "kids_trackpant", "kids_joggers",
}

TRADITIONAL_CATEGORY_TOKENS = {
    "mens_sherwani", "mens_pathani_suit", "mens_nehru_jacket", "mens_kurta_pajama",
    "womens_sarees", "womens_lehenga", "womens_saree_blouse",
    "kids_sherwani", "kids_pathani_suit", "kids_nehru_jacket", "kids_kurta_pajama",
}

ETHNIC_CATEGORY_TOKENS = {
    "womens_anarkali", "womens_sharara", "womens_palazzo",
}

PARTY_CATEGORY_TOKENS = {
    "womens_party_dress", "womens_midi_dress", "womens_maxi_dress",
}


def normalize_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalized_title_key(title, brand=""):
    text = f"{brand} {title}".lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_colors(text):
    text_lower = (text or "").lower()
    return sorted({color for color in COLOR_KEYWORDS if color in text_lower})


def infer_fit(text):
    text_lower = (text or "").lower()
    for fit, keywords in FIT_KEYWORDS.items():
        if any(keyword in text_lower for keyword in keywords):
            return fit
    return "regular"


def infer_style_tags(text):
    text_lower = (text or "").lower()
    tags = []
    for style, keywords in STYLE_KEYWORDS.items():
        if any(keyword in text_lower for keyword in keywords):
            tags.append(style)
    return tags


def infer_gender(title="", description="", category="", current_gender="", product_url=""):
    # 1. Prioritize existing gender from dataset if it's already a standard value
    current = (current_gender or "").lower().strip()
    if current in {"female", "women", "womens", "woman", "ladies"}:
        return "women"
    if current in {"male", "men", "mens", "man"}:
        return "men"
    if current in {"kids", "kid", "child", "children", "boys", "girls", "junior", "infant"}:
        return "kids"

    # 2. Fallback to keyword-based heuristic parsing with word boundary logic
    primary_text = f"{title} {description} {product_url}".lower()
    text = f"{primary_text} {category}".lower()
    category_lower = (category or "").lower()

    # Tokenize text into words/numbers
    words = set(re.findall(r"[a-z0-9]+", primary_text))
    words_with_category = set(re.findall(r"[a-z0-9]+", text))

    explicit_kids_hits = sum(1 for token in EXPLICIT_KIDS_SIGNALS if token in words)
    if explicit_kids_hits:
        return "kids"

    explicit_women_hits = sum(1 for token in EXPLICIT_WOMEN_SIGNALS if token in words)
    if explicit_women_hits:
        return "women"

    # Evaluate men signals excluding explicit women signals
    men_eval_words = words - set(EXPLICIT_WOMEN_SIGNALS)
    explicit_men_hits = sum(1 for token in EXPLICIT_MEN_SIGNALS if token in men_eval_words)
    if explicit_men_hits:
        return "men"

    primary_women_hits = sum(1 for token in WOMEN_SIGNALS if token in words)
    primary_men_eval_words = words - set(WOMEN_SIGNALS)
    primary_men_hits = sum(1 for token in MEN_SIGNALS if token in primary_men_eval_words)

    if primary_women_hits > primary_men_hits:
        return "women"
    if primary_men_hits > primary_women_hits:
        return "men"

    women_hits = sum(1 for token in WOMEN_SIGNALS if token in words_with_category)
    men_eval_words_with_category = words_with_category - set(WOMEN_SIGNALS)
    men_hits = sum(1 for token in MEN_SIGNALS if token in men_eval_words_with_category)

    if women_hits > men_hits:
        return "women"
    if men_hits > women_hits:
        return "men"

    if category_lower.startswith("womens_"):
        return "women"
    if category_lower.startswith("mens_"):
        return "men"
    if category_lower.startswith("kids_"):
        return "kids"

    return "unisex"


def infer_category(title="", description="", gender="", current_category=""):
    gender = (gender or "").lower().strip()
    current = (current_category or "").lower().strip()

    # 1. Prioritize existing category if it matches the inferred gender
    if gender == "women" and current.startswith("womens_"):
        return current
    if gender == "men" and current.startswith("mens_"):
        return current
    if gender == "kids" and current.startswith("kids_"):
        return current

    # 2. Fallback to keyword matching heuristics using word tokenization
    primary_text = f"{title} {description}".lower()
    text = f"{primary_text} {current}".lower()
    words = set(re.findall(r"[a-z0-9]+", text))

    if gender == "women":
        mapping = WOMEN_CATEGORY_BY_TOKEN
    elif gender == "kids":
        mapping = KIDS_CATEGORY_BY_TOKEN
    else:
        mapping = MEN_CATEGORY_BY_TOKEN

    for token, category in mapping.items():
        # Check if the token words are subset of text words
        token_words = re.findall(r"[a-z0-9]+", token.lower())
        if all(w in words for w in token_words):
            return category

    if gender == "women" and current.startswith("mens_"):
        return "other"
    if gender == "men" and current.startswith("womens_"):
        return "other"
    if gender in {"men", "women"} and current.startswith("kids_"):
        return "other"
    if gender == "kids" and (current.startswith("mens_") or current.startswith("womens_")):
        base = current.split("_", 1)[1]
        return f"kids_{base}"
    return current or "other"


def infer_category_type(title="", description="", category="", current_category_type=""):
    current = normalize_text(current_category_type)
    if current in {"Casual", "Ethnic", "Formal", "Party Wear", "Sportswear", "Traditional"}:
        return current

    category = (category or "").lower()
    text = f"{title} {description} {category}".lower()
    words = set(re.findall(r"[a-z0-9]+", text))

    # Fallback to category list checks and keyword matching
    if category in SPORTS_CATEGORY_TOKENS or any(token in words for token in ["trackpant", "activewear", "gym", "training"]) or "track pant" in text:
        return "Sportswear"
    if category in TRADITIONAL_CATEGORY_TOKENS or any(token in words for token in ["sherwani", "pathani", "nehru", "saree", "lehenga"]):
        return "Traditional"
    if category in ETHNIC_CATEGORY_TOKENS or any(token in words for token in ["anarkali", "sharara", "dupatta", "kurta", "palazzo"]):
        return "Ethnic"
    if category in FORMAL_CATEGORY_TOKENS or any(token in words for token in ["blazer", "chinos"]) or any(kw in text for kw in ["formal shirt", "formal trouser", "formal trousers", "business suit"]):
        return "Formal"
    if category in PARTY_CATEGORY_TOKENS:
        return "Party Wear"

    return "Casual"



def clean_product_values(title, brand, gender, category, description, category_type="", product_url=""):
    title = normalize_text(title)
    brand = normalize_text(brand)
    description = normalize_text(description) or title
    clean_gender = infer_gender(title, description, category, gender, product_url)
    clean_category = infer_category(title, description, clean_gender, category)
    clean_category_type = infer_category_type(title, description, clean_category, category_type)
    combined_text = f"{title} {description} {clean_category} {product_url}"

    return {
        "title": title,
        "brand": brand,
        "gender": clean_gender,
        "category": clean_category,
        "category_type": clean_category_type,
        "description": description,
        "colors": extract_colors(combined_text),
        "fit": infer_fit(combined_text),
        "style_tags": infer_style_tags(combined_text),
    }

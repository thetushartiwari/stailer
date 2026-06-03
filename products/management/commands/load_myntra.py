# products/management/commands/load_myntra.py
import json
import os
import re
from django.core.management.base import BaseCommand
from products.catalog_cleaning import COLOR_KEYWORDS, FIT_KEYWORDS, STYLE_KEYWORDS, clean_product_values
from products.models import Product

GENDER_KEYWORDS = {
    "women": ["women", "woman", "girl", "female", "ladies", "girls"],
    "men": ["men", "man", "boy", "male", "boys"]
}

CATEGORY_KEYWORDS = {
    "tshirts": ["tshirt", "t-shirt", "tee", "polo"],
    "jeans": ["jeans", "denim", "trouser", "pants", "shorts"],
    "dresses": ["dress", "midi", "maxi", "saree", "kurti", "gown", "flared"],
    "kurtas": ["kurta", "nehru", "ethnic", "traditional", "kurta set"],
    "jackets": ["jacket", "coat", "blazer", "puffer", "bomber", "windcheater"],
    "innerwear": ["lounge", "innerwear", "vest", "boxer"],
}

def infer_gender(title, product_url):
    text = f"{title} {product_url}".lower()
    if "unisex" in text:
        return "unisex"
    for gender, keywords in GENDER_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return gender
    return "unisex"


def infer_category(title, product_url):
    text = f"{title} {product_url}".lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return cat
    # fallback to path segments if pattern not matched
    url_parts = product_url.lower().split('/')
    for part in url_parts:
        for cat in CATEGORY_KEYWORDS:
            if cat in part:
                return cat
    return "other"


def infer_colors(title, product_url):
    text = f"{title} {product_url}".lower()
    colors = []
    for color in COLOR_KEYWORDS:
        if color in text and color not in colors:
            colors.append(color)
    return colors


def infer_fit(title, product_url):
    text = f"{title} {product_url}".lower()
    for fit, keywords in FIT_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return fit
    return ""


def infer_style_tags(title, product_url):
    text = f"{title} {product_url}".lower()
    tags = []
    for style, keywords in STYLE_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            tags.append(style)
    return tags

class Command(BaseCommand):
    help = "Loads Myntra dataset from myntra_data.json into the database"

    def handle(self, *args, **options):
        json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "myntra_data.json")
        
        if not os.path.exists(json_path):
            self.stdout.write(self.style.ERROR(f"Dataset file not found at {json_path}"))
            return

        self.stdout.write(f"Reading dataset from {json_path}...")
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                products_list = json.load(f)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to parse JSON file: {e}"))
            return

        self.stdout.write(f"Found {len(products_list)} products. Clearing existing products...")
        Product.objects.all().delete()

        created_count = 0
        for p in products_list:
            title = p.get("title", "Premium Apparel")
            brand = p.get("brand", "Stailer")
            price_str = p.get("price", "Rs. 999")
            image_url = p.get("image_url", p.get("image_link", ""))
            product_url = p.get("product_url", "")
            description = p.get("description", "")

            # Format title with brand if it doesn't already have it
            if brand.lower() not in title.lower():
                title = f"{brand} {title}"

            # Parse price to float correctly, removing "Rs." and periods from abbreviation
            price_clean = price_str.replace("Rs.", "").replace("Rs", "").replace("₹", "").strip()
            try:
                price_num = float(re.sub(r"[^\d]", "", price_clean))
            except ValueError:
                price_num = 999.0

            if not image_url or not product_url:
                continue

            cleaned = clean_product_values(
                title,
                brand,
                infer_gender(title, product_url),
                infer_category(title, product_url),
                description,
                "",
                product_url,
            )

            Product.objects.create(
                title=cleaned["title"],
                brand=cleaned["brand"],
                gender=cleaned["gender"],
                category=cleaned["category"],
                category_type=cleaned["category_type"],
                colors=cleaned["colors"],
                fit=cleaned["fit"],
                style_tags=cleaned["style_tags"],
                price=price_num,
                description=cleaned["description"],
                product_url=product_url,
                image_url=image_url
            )
            created_count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully loaded {created_count} products into the database!"))

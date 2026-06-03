# products/management/commands/load_clothing_dataset.py
import re
import os
import pandas as pd
from django.core.management.base import BaseCommand
from products.catalog_cleaning import clean_product_values
from products.models import Product

class Command(BaseCommand):
    help = "Loads clothing_dataset.xlsx into the Django Product database"

    def handle(self, *args, **options):
        # Path to clothing_dataset.xlsx inside the root folder
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        excel_path = os.path.join(base_dir, "clothing_dataset.xlsx")

        if not os.path.exists(excel_path):
            self.stdout.write(self.style.ERROR(f"Dataset Excel file not found at {excel_path}"))
            return

        self.stdout.write(f"Reading dataset from {excel_path}...")
        try:
            df = pd.read_excel(excel_path)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to parse Excel file: {e}"))
            return

        self.stdout.write(f"Found {len(df)} products in sheet. Clearing existing products...")
        Product.objects.all().delete()

        created_count = 0
        skipped_count = 0

        for index, row in df.iterrows():
            product_name = str(row.get("product_name", "Premium Apparel")).strip()
            brand = str(row.get("brand", "Stailer")).strip()
            gender_raw = str(row.get("gender", "unisex")).strip().lower()
            category_type = str(row.get("category_type", "Casual")).strip()
            category_name = str(row.get("category_name", "other")).strip()
            description = str(row.get("description", "")).strip()
            price_str = str(row.get("price", "999"))
            rating_val = row.get("rating", 0.0)
            image_url = str(row.get("image_url", "")).strip()
            product_url = str(row.get("product_url", "")).strip()

            # Parse and clean price string (e.g. 'Rs. 4319' or 'Rs. 4,319')
            price_clean = price_str.replace("Rs.", "").replace("Rs", "").replace("₹", "").replace(",", "").strip()
            try:
                price_num = float(re.sub(r"[^\d\.]", "", price_clean))
            except ValueError:
                price_num = 999.0

            # Parse rating
            try:
                rating = float(rating_val)
            except (ValueError, TypeError):
                rating = 0.0

            # Guardrails to ensure product has basic URL info
            if not image_url or not product_url or image_url == "nan" or product_url == "nan":
                skipped_count += 1
                continue

            # Format product name with brand if it doesn't already have it
            if brand.lower() not in product_name.lower():
                product_name = f"{brand} {product_name}"

            cleaned = clean_product_values(
                product_name,
                brand,
                gender_raw,
                category_name,
                description,
                category_type,
                product_url,
            )

            # Create product record
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
                rating=rating,
                description=cleaned["description"],
                product_url=product_url,
                image_url=image_url
            )
            created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Successfully populated database: Created {created_count} products (Skipped {skipped_count} invalid rows)!"
        ))
        
        # Trigger dynamic similarity cache rebuilding
        self.stdout.write("Building recommendation similarity cached matrix...")
        from products.recommendation_model import invalidate_recommendation_cache
        invalidate_recommendation_cache()
        self.stdout.write(self.style.SUCCESS("Pickled similarity caches built successfully!"))

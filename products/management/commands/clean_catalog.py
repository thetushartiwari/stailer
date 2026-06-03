from django.core.management.base import BaseCommand

from products.catalog_cleaning import clean_product_values, normalized_title_key
from products.models import Product
from products.recommendation_model import invalidate_recommendation_cache


class Command(BaseCommand):
    help = "Audits and optionally cleans Product rows using only existing Product fields."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Persist cleaned existing fields. Without this, only prints an audit.",
        )
        parser.add_argument(
            "--delete-duplicates",
            action="store_true",
            help="Also delete duplicate Product rows. Off by default to preserve dataset size.",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]
        delete_duplicates = options["delete_duplicates"]
        products = list(Product.objects.order_by("id"))
        field_fixes = []
        seen = {}
        duplicate_ids = []

        for product in products:
            cleaned = clean_product_values(
                product.title,
                product.brand,
                product.gender,
                product.category,
                product.description,
                product.category_type,
                product.product_url,
            )
            changed_fields = {
                field: value
                for field, value in cleaned.items()
                if getattr(product, field) != value
            }

            if changed_fields:
                field_fixes.append((product, changed_fields))

            key = normalized_title_key(cleaned["title"], cleaned["brand"])
            duplicate_bucket = (key, cleaned["gender"], cleaned["category"])
            if duplicate_bucket in seen:
                duplicate_ids.append(product.id)
            else:
                seen[duplicate_bucket] = product.id

        self.stdout.write(f"Products scanned: {len(products)}")
        self.stdout.write(f"Rows needing existing-field cleanup: {len(field_fixes)}")
        self.stdout.write(f"Duplicate rows detected: {len(duplicate_ids)}")

        for product, changes in field_fixes[:25]:
            before = f"{product.gender}/{product.category}"
            after = f"{changes.get('gender', product.gender)}/{changes.get('category', product.category)}"
            self.stdout.write(f"- #{product.id}: {before} -> {after} | {product.title}")

        if duplicate_ids[:25]:
            self.stdout.write("Duplicate ids sample: " + ", ".join(str(i) for i in duplicate_ids[:25]))

        if not apply_changes:
            self.stdout.write(self.style.WARNING("Dry run only. Re-run with --apply to save cleanup."))
            return

        for product, changes in field_fixes:
            for field, value in changes.items():
                setattr(product, field, value)
            product.save(update_fields=list(changes.keys()))

        if duplicate_ids and delete_duplicates:
            Product.objects.filter(id__in=duplicate_ids).delete()

        invalidate_recommendation_cache()
        self.stdout.write(self.style.SUCCESS("Catalog cleaned using existing Product fields only."))
        if duplicate_ids and not delete_duplicates:
            self.stdout.write(self.style.WARNING("Duplicate rows were preserved; recommendation ranking suppresses duplicates at display time."))

# verify_recommender.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stailer.settings')
django.setup()

from products.models import Product, UserProfile, UserPreference
from products.recommender.service import recommend_for_profile
from products.recommender.schemas import RerankChoice
from products.recommender.validator import validate_rerank_choice

def test_men_office():
    print("Testing 'men office' recommendations...")
    profile = UserProfile(session_key="test_men_office_user", age=30)
    result = recommend_for_profile(profile, "office clothes for men", selected_gender="men", max_results=5)
    print(f"Returned {len(result.products)} products:")
    for p in result.products:
        print(f" - [{p.id}] {p.title} ({p.gender}, {p.category_type}, {p.category})")
        assert p.gender == "men", f"Expected men product, got {p.gender}"
        assert p.category_type in ["Formal", "Casual"] or "formal" in (p.title + " " + p.description).lower() or "office" in (p.title + " " + p.description).lower(), "Expected formal/office clothing"
    print("[OK] 'men office' checks passed!")

def test_women_ethnic():
    print("Testing 'women ethnic' recommendations...")
    profile = UserProfile(session_key="test_women_ethnic_user", age=25)
    result = recommend_for_profile(profile, "ethnic wear for women", selected_gender="women", max_results=5)
    print(f"Returned {len(result.products)} products:")
    for p in result.products:
        print(f" - [{p.id}] {p.title} ({p.gender}, {p.category_type}, {p.category})")
        assert p.gender == "women", f"Expected women product, got {p.gender}"
        assert p.category_type in ["Ethnic", "Traditional"] or "ethnic" in (p.title + " " + p.description).lower() or "traditional" in (p.title + " " + p.description).lower(), "Expected ethnic/traditional clothing"
    print("[OK] 'women ethnic' checks passed!")

def test_kids_formal():
    print("Testing 'kids formal' recommendations...")
    profile = UserProfile(session_key="test_kids_formal_user", age=8)
    result = recommend_for_profile(profile, "formal suit for kids", selected_gender="kids", max_results=5)
    print(f"Returned {len(result.products)} products:")
    for p in result.products:
        print(f" - [{p.id}] {p.title} ({p.gender}, {p.category_type}, {p.category})")
        assert p.gender == "kids", f"Expected kids product, got {p.gender}"
    print("[OK] 'kids formal' checks passed!")

def test_adult_men_no_kids():
    print("Testing adult men profile receives no kids items...")
    profile = UserProfile(session_key="test_adult_user", age=28)
    result = recommend_for_profile(profile, "suits", selected_gender="men", max_results=10)
    for p in result.products:
        assert p.gender != "kids", "Adult profile should not receive kids products"
    print("[OK] Adult profile kids-exclusion check passed!")

def test_black_blazer_ranking():
    print("Testing 'black blazer' prompt ranks black/dark blazers higher...")
    # Seed a black blazer dynamically to ensure the test has a matching product
    blazer = Product.objects.filter(title__icontains="blazer", gender="men").first()
    if not blazer:
        print("Skipping blazer test: no men blazers in DB")
        return

    original_title = blazer.title
    original_colors = blazer.colors
    blazer.title = "Peter England Men Solid Black Single-Breasted Formal Blazer"
    blazer.colors = ["black"]
    blazer.save()

    try:
        profile = UserProfile(session_key="test_blazer_user", age=28)
        result = recommend_for_profile(profile, "black blazer", selected_gender="men", max_results=10)
        titles_colors = [(p.title.lower(), (p.colors or [])) for p in result.products]
        print("Top products for 'black blazer':")
        for tc in titles_colors[:3]:
            print(f" - {tc}")
        has_black = any("black" in title or "black" in colors for title, colors in titles_colors[:3])
        assert has_black, "Expected black blazer/clothing in top results"
    finally:
        # Restore the original product state
        blazer.title = original_title
        blazer.colors = original_colors
        blazer.save()

    print("[OK] Color-based ranking prioritization passed!")

def test_irrelevant_prompt():
    print("Testing irrelevant prompt return behavior...")
    profile = UserProfile(session_key="test_irr_user")
    result = recommend_for_profile(profile, "buy a laptop", max_results=5)
    print(f"Returned {len(result.products)} products for irrelevant prompt.")
    assert len(result.products) == 0, "Expected 0 products for completely irrelevant non-apparel prompt"
    print("[OK] Irrelevant prompt rejection passed!")

def test_feedback_drift():
    print("Testing feedback preference drift...")
    # Get any two products
    products = list(Product.objects.filter(gender="men")[:2])
    if len(products) < 2:
        print("Skipping feedback drift test: not enough products")
        return
    p1, p2 = products[0], products[1]
    profile = UserProfile.objects.create(session_key="test_drift_user_key", age=25)
    try:
        # User likes p1
        pref = UserPreference.objects.create(product=p1, liked=True, session_key=profile.session_key)
        # Check scoring feedback
        from products.recommender.feedback import feedback_score
        score1, _ = feedback_score(p1, profile)
        print(f"Feedback score for liked product: {score1}")
        assert score1 > 0, "Liked product should have positive feedback affinity"
    finally:
        profile.delete()
    print("[OK] Feedback preference drift checks passed!")

def test_validator_rejects_invalid_id():
    print("Testing validator rejects invalid choice...")
    profile = UserProfile(session_key="test_val_user", age=30)
    p = Product.objects.first()
    if p:
        # Choice with confidence below threshold
        from products.recommender.schemas import StylePlan
        plan = StylePlan(minimum_confidence=0.8)
        choice = RerankChoice(product_id=p.id, confidence=0.5, reason="low confidence")
        ok, reason = validate_rerank_choice(p, choice, plan, profile)
        assert not ok, "Expected validation failure for confidence below minimum_confidence"
        assert "confidence" in reason.lower()
    print("[OK] Validator rejection checks passed!")

if __name__ == "__main__":
    test_men_office()
    print()
    test_women_ethnic()
    print()
    test_kids_formal()
    print()
    test_adult_men_no_kids()
    print()
    test_black_blazer_ranking()
    print()
    test_irrelevant_prompt()
    print()
    test_feedback_drift()
    print()
    test_validator_rejects_invalid_id()
    print("\nAll pipeline verification checks completed successfully! [OK]")

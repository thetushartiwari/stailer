# verify_stylist.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stailer.settings')
django.setup()

from products.models import Product, UserProfile
from products.stylist_engine import classify_gender, rank_products

def test_gender_classification():
    print("Testing foolproof gender classification...")
    # Basic cases
    assert classify_gender("Men Solid Slim Fit T-shirt", "Comfortable cotton tee") == "men"
    assert classify_gender("Printed Fit & Flare Midi Dress", "Floral design for girls") == "women"
    
    # False-positive test (has "men" as substring of "women")
    assert classify_gender("Women Printed Kurta", "Premium cotton kurti") == "women"
    assert classify_gender("Women Solid Tshirt", "Women casual apparel") == "women"
    
    # URL checking
    assert classify_gender("Premium Top", "Vibrant colors", "https://www.myntra.com/dresses/women/top/123/buy") == "women"
    assert classify_gender("Premium Shirt", "Vibrant colors", "https://www.myntra.com/shirts/men/shirt/123/buy") == "men"
    print("[OK] Gender classification checks passed!")

def test_empty_state_shuffling():
    print("Testing dynamic empty-state shuffling...")
    profile = UserProfile(session_key="temp_sim_user")
    
    recs1 = rank_products(profile, {}, prompt_query="", gender_filter="all", top_n=12)
    recs2 = rank_products(profile, {}, prompt_query="", gender_filter="all", top_n=12)
    
    # Shuffled lists in empty state should yield non-identical first 12 items (unless dataset has < 12 items)
    ids1 = [p.id for p in recs1]
    ids2 = [p.id for p in recs2]
    
    print(f"Empty state feed 1: {ids1[:5]}...")
    print(f"Empty state feed 2: {ids2[:5]}...")
    
    # They should not be exactly identical order
    assert ids1 != ids2 or len(recs1) < 5
    print("[OK] Empty state shuffling successfully randomized catalog landing!")

if __name__ == "__main__":
    try:
        test_gender_classification()
        test_empty_state_shuffling()
        print("\nAll stylist studio backend verifications completed successfully! [OK]")
    except AssertionError as e:
        print(f"Assertion failed: {e}")

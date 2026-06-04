from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Product, UserPreference, UserProfile
from .stylist_engine import (
    update_preferences, SKIN_TONE_COLORS,
    predict_skin_tone_from_rgb, predict_body_shape
)
from .recommender import recommend_for_profile

def get_session_key(request):
    """Ensure every user (even anonymous) has a session key."""
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key

def get_or_create_profile(request):
    """Retrieve or create UserProfile for the current user/session."""
    session_key = get_session_key(request)
    if request.user.is_authenticated:
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        if created or not profile.session_key:
            profile.session_key = session_key
            profile.save()
        return profile
    else:
        profile, _ = UserProfile.objects.get_or_create(session_key=session_key)
        return profile

def landing_page(request):
    """Sleek dark-mode Studio Diagnostic landing page. Displays NO products."""
    profile = get_or_create_profile(request)
    
    # Handle GET request: render empty diagnostic form
    return render(request, "products/landing.html", {
        "profile": profile,
        "skin_tone_colors": SKIN_TONE_COLORS
    })


@csrf_exempt
def diagnose_dna(request):
    """Saves diagnosed measurements and initial prompt, then redirects to recommendations."""
    if request.method == "POST":
        profile = get_or_create_profile(request)
        
        # 1. Parse biometrics measurements
        try:
            height = float(request.POST.get("height", 0))
            weight = float(request.POST.get("weight", 0))
            bust = float(request.POST.get("bust", 0))
            waist = float(request.POST.get("waist", 0))
            hips = float(request.POST.get("hips", 0))
        except (ValueError, TypeError):
            height = weight = bust = waist = hips = 0.0

        profile.height = height
        profile.weight = weight
        profile.bust_size = bust
        profile.waist_size = waist
        profile.hips_size = hips

        gender = request.POST.get("gender", "all")

        # 2. Predict Body Silhouette using Supervised ML or Manual Override
        manual_body_type = request.POST.get("manual_body_type", "").strip()
        if manual_body_type:
            profile.body_type = manual_body_type
        elif height and weight and bust and waist and hips:
            body_type = predict_body_shape(height, weight, bust, waist, hips, gender=gender)
            profile.body_type = body_type
        
        # 3. Parse Skin Tone
        skin_tone = request.POST.get("skin_tone", "").strip()
        if skin_tone:
            profile.skin_tone = skin_tone
            
        # Parse Name & Age
        user_name = request.POST.get("user_name", "").strip()
        age_str = request.POST.get("age", "").strip()
        try:
            age = int(age_str) if age_str else None
        except ValueError:
            age = None

        if user_name:
            profile.user_name = user_name
        if age is not None:
            profile.age = age

        profile.save()

        # 4. Save initial prompt to session history
        prompt = request.POST.get("prompt", "").strip()
        request.session['stylist_history'] = []
        if prompt:
            request.session['stylist_history'] = [
                {"query": prompt, "intent": {}}
            ]
            request.session.modified = True

        return redirect(f"/recommendations/?gender={gender}")
        
    return redirect("landing_page")

def recommendations_page(request):
    """Displays the dynamic Curated Rack matching the session's prompt and DNA."""
    profile = get_or_create_profile(request)
    gender = request.GET.get("gender", "all")

    # Retrieve conversational prompt context
    history = request.session.get('stylist_history', [])
    combined_query = ""
    latest_intent = {}
    stylist_response = ""

    if history:
        # Re-build combined textual search from history stack
        combined_query = " ".join([h["query"] for h in history])
        latest_intent = history[-1].get("intent", {})
        stylist_response = latest_intent.get("stylist_response", "")

    if not stylist_response:
        name_str = f"Hi {profile.user_name}, " if profile.user_name else "Hi! "
        dna_parts = []
        if profile.body_type:
            dna_parts.append(f"{profile.body_type.lower()} body shape")
        if profile.skin_tone:
            dna_parts.append(f"{profile.skin_tone.lower()} skin tone")
        dna_desc = " and ".join(dna_parts)
        dna_str = f" designed for your {dna_desc}" if dna_parts else ""
        stylist_response = f"{name_str}Welcome to your premium fashion diagnostic workspace. Input your parameters and ask stAiler to reveal your curated rack{dna_str}."

    result = recommend_for_profile(
        profile=profile,
        prompt=combined_query,
        selected_gender=gender,
        max_results=12,
    )
    recommended = result.products
    if combined_query:
        stylist_response = result.stylist_response

    return render(request, "products/recommendations.html", {
        "recommended": recommended,
        "profile": profile,
        "gender": gender,
        "history": history,
        "combined_query": combined_query,
        "stylist_response": stylist_response
    })

@csrf_exempt
def refine_prompt(request):
    """Conversational Session Refiner Console: blends prompts and re-runs recommendations."""
    if request.method == "POST":
        profile = get_or_create_profile(request)
        new_prompt = request.POST.get("prompt", "").strip()
        gender = request.POST.get("gender", "all")

        if not new_prompt:
            return JsonResponse({"success": False, "message": "Prompt cannot be empty."})

        # Retrieve history array
        history = request.session.get('stylist_history', [])

        # Context Blending: merge previous query context
        combined_prompt = new_prompt
        if history:
            previous_query = history[-1]["query"]
            # Blend prompts: prepend previous garments/context to guide search
            combined_prompt = f"{previous_query} {new_prompt}"

        # Update history stack
        history.append({"query": combined_prompt, "intent": {}})
        request.session['stylist_history'] = history
        request.session.modified = True

        result = recommend_for_profile(
            profile=profile,
            prompt=combined_prompt,
            selected_gender=gender,
            max_results=12,
        )
        new_recs = result.products

        recs_data = [{
            "id": r.id,
            "title": r.title,
            "brand": r.brand,
            "price": r.price,
            "image_url": r.image_url,
            "product_url": r.product_url,
            "match_score": getattr(r, "match_score", 80),
            "match_explanations": getattr(r, "match_explanations", [])
        } for r in new_recs]

        stylist_response = result.stylist_response

        return JsonResponse({
            "success": True,
            "recommendations": recs_data,
            "stylist_response": stylist_response,
            "combined_query": combined_prompt
        })

    return JsonResponse({"success": False, "message": "Invalid request method."}, status=400)

@csrf_exempt
def reset_stylist(request):
    """Clears conversational prompt logs and redirects back to Landing diagnostic console."""
    request.session['stylist_history'] = []
    request.session.modified = True
    return redirect("landing_page")

@csrf_exempt
def toggle_like(request, product_id):
    """Handles Likes/Dislikes preference and triggers online statistical learning weights drift."""
    if request.method == "POST":
        liked = request.POST.get("liked") == "true"
        gender_filter = request.POST.get("gender", "all")
        product = get_object_or_404(Product, id=product_id)
        profile = get_or_create_profile(request)

        pref, _ = UserPreference.objects.get_or_create(
            product=product,
            session_key=profile.session_key,
            user=request.user if request.user.is_authenticated else None,
        )
        pref.liked = liked
        pref.save()

        # Trigger statistical online weights drift update
        update_preferences(profile, product, "like" if liked else "dislike")

        # Re-fetch history
        history = request.session.get('stylist_history', [])
        combined_query = ""
        if history:
            combined_query = " ".join([h["query"] for h in history])

        result = recommend_for_profile(
            profile=profile,
            prompt=combined_query,
            selected_gender=gender_filter,
            max_results=12,
        )
        new_recs = result.products

        recs_data = [{
            "id": r.id,
            "title": r.title,
            "brand": r.brand,
            "price": r.price,
            "image_url": r.image_url,
            "product_url": r.product_url,
            "match_score": getattr(r, "match_score", 80),
            "match_explanations": getattr(r, "match_explanations", [])
        } for r in new_recs]

        return JsonResponse({
            "success": True, 
            "message": "Styling preferences synchronized successfully.",
            "recommendations": recs_data
        })
        
    return JsonResponse({"success": False, "message": "Invalid method."})

@csrf_exempt
def update_skin_tone(request):
    """Supervised CV skin tone classification endpoint via base64 frame POSTs."""
    if request.method == "POST":
        rgb_data = request.POST.get("rgb_values")
        profile = get_or_create_profile(request)
        
        try:
            rgb_list = json.loads(rgb_data) # [R, G, B]
            skin_tone = predict_skin_tone_from_rgb(rgb_list)
        except Exception:
            return JsonResponse({"success": False, "message": "Invalid RGB pixel data."})

        profile.skin_tone = skin_tone
        profile.save()

        return JsonResponse({
            "success": True,
            "skin_tone": skin_tone,
            "recommended_colors": SKIN_TONE_COLORS.get(skin_tone.lower(), [])
        })

    return JsonResponse({"success": False, "message": "Invalid method."})

@csrf_exempt
def update_filters(request):
    """Dynamic sidebar synchronizations for manual filter overrides."""
    if request.method == "POST":
        profile = get_or_create_profile(request)
        
        checked_brands = request.POST.getlist("brands[]")
        checked_fits = request.POST.getlist("fits[]")
        checked_categories = request.POST.getlist("categories[]")
        budget_limit = request.POST.get("budget_limit")
        gender_filter = request.POST.get("gender", "all")
        
        filters = profile.personalization_filters or {}
        filters["checked_brands"] = checked_brands
        filters["checked_fits"] = checked_fits
        filters["checked_categories"] = checked_categories
        
        if budget_limit and budget_limit != "0" and budget_limit != "":
            filters["budget_limit"] = budget_limit
        else:
            filters["budget_limit"] = None
            
        profile.personalization_filters = filters
        profile.save()
        
        # Fetch refined rack
        history = request.session.get('stylist_history', [])
        combined_query = " ".join([h["query"] for h in history]) if history else ""
        result = recommend_for_profile(
            profile=profile,
            prompt=combined_query,
            selected_gender=gender_filter,
            max_results=12,
        )
        new_recs = result.products
        
        recs_data = [{
            "id": r.id,
            "title": r.title,
            "brand": r.brand,
            "price": r.price,
            "image_url": r.image_url,
            "product_url": r.product_url,
            "match_score": getattr(r, "match_score", 80),
            "match_explanations": getattr(r, "match_explanations", [])
        } for r in new_recs]
        
        return JsonResponse({
            "success": True,
            "recommendations": recs_data,
            "message": "DNA filters mapped successfully."
        })
        
    return JsonResponse({"success": False, "message": "Invalid method."}, status=400)

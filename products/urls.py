from django.urls import path
from . import views

urlpatterns = [
    # Main Styling Pipelines
    path('', views.landing_page, name='landing_page'),
    path('diagnose/', views.diagnose_dna, name='diagnose_dna'),
    path('recommendations/', views.recommendations_page, name='recommendations_page'),
    path('refine/', views.refine_prompt, name='refine_prompt'),
    path('reset/', views.reset_stylist, name='reset_stylist'),
    
    # Session Preferences & Toggles
    path('toggle-like/<int:product_id>/', views.toggle_like, name='toggle_like'),
    path('stylist/update-skin-tone/', views.update_skin_tone, name='update_skin_tone'),
    path('stylist/update-filters/', views.update_filters, name='update_filters'),
    
]

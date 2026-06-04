from django.db import models
from django.contrib.auth.models import User

class Product(models.Model):
    title = models.CharField(max_length=200, default="")
    brand = models.CharField(max_length=100, default="", blank=True)
    gender = models.CharField(max_length=20, default="unisex", db_index=True)
    category = models.CharField(max_length=100, default="", blank=True, db_index=True)
    category_type = models.CharField(max_length=100, default="", blank=True)
    colors = models.JSONField(default=list, blank=True)
    fit = models.CharField(max_length=50, default="", blank=True)
    style_tags = models.JSONField(default=list, blank=True)
    price = models.FloatField(default=0.0)
    rating = models.FloatField(default=0.0)
    description = models.TextField(default="")
    product_url = models.URLField(max_length=500, default="")
    image_url = models.URLField(max_length=500, default="")

    def __str__(self):
        return f"{self.brand} {self.title}".strip() if self.brand else self.title


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=100, null=True, blank=True)
    user_name = models.CharField(max_length=100, null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)
    skin_tone = models.CharField(max_length=50, null=True, blank=True)  # Fair, Medium, Olive, Deep
    gender = models.CharField(max_length=20, default="all", blank=True)
    body_type = models.CharField(max_length=50, null=True, blank=True)
    bmi_category = models.CharField(max_length=50, default="Normal", blank=True)
    height = models.FloatField(null=True, blank=True)
    weight = models.FloatField(null=True, blank=True)
    bust_size = models.FloatField(null=True, blank=True)
    waist_size = models.FloatField(null=True, blank=True)
    hips_size = models.FloatField(null=True, blank=True)
    profile_tags = models.JSONField(default=dict, blank=True)
    personalization_filters = models.JSONField(default=dict, blank=True)

    def __str__(self):
        owner = self.user.username if self.user else (self.session_key or "anonymous")
        return f"Profile for {owner} - Skin Tone: {self.skin_tone}"


class UserPreference(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=100, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    liked = models.BooleanField(default=True)  # True = liked, False = disliked

    def __str__(self):
        owner = self.user.username if self.user else (self.session_key or "anon")
        return f"{owner} - {self.product.title} ({'Liked' if self.liked else 'Disliked'})"


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    def __str__(self):
        return f"Cart {self.id} for {self.user or self.session_key}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('cart', 'product')

    def subtotal(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product.title}"


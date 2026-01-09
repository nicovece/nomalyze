from django.contrib import admin
from .models import Recipe


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ["name", "cooking_time", "difficulty", "likes"]
    list_filter = ["difficulty", "cooking_time"]
    search_fields = ["name", "ingredients"]
    readonly_fields = ["difficulty", "likes", "comments"]

    fieldsets = (
        ("Basic Information", {"fields": ("name", "short_description", "ingredients", "cooking_time", "recipe_image")}),
        ("Calculated Fields", {"fields": ("difficulty", "likes", "comments"), "classes": ("collapse",)}),
        ("Additional Information", {"fields": ("references",)}),
    )

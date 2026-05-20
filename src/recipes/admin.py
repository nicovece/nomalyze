from django.contrib import admin
from .models import Recipe


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ["name", "status", "cooking_time", "difficulty", "likes"]
    list_filter = ["status", "difficulty", "cooking_time"]
    search_fields = ["name", "ingredients"]
    readonly_fields = ["difficulty", "likes", "comments"]
    actions = ["make_published", "make_draft"]

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "name",
                    "short_description",
                    "ingredients",
                    "cooking_time",
                    "recipe_image",
                    "status",
                ),
            },
        ),
        (
            "Calculated Fields",
            {"fields": ("difficulty", "likes", "comments"), "classes": ("collapse",)},
        ),
        ("Additional Information", {"fields": ("references",)}),
    )

    @admin.action(description="Publish selected recipes")
    def make_published(self, request, queryset):
        updated = queryset.update(status=Recipe.Status.PUBLISHED)
        self.message_user(request, f"{updated} recipe(s) published.")

    @admin.action(description="Move selected recipes back to draft")
    def make_draft(self, request, queryset):
        updated = queryset.update(status=Recipe.Status.DRAFT)
        self.message_user(request, f"{updated} recipe(s) moved to draft.")

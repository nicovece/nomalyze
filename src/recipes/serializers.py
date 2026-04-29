from rest_framework import serializers
from .models import Recipe
from .templatetags.recipe_extras import media_to_static


class RecipeSerializer(serializers.ModelSerializer):
    ingredients_list = serializers.SerializerMethodField()
    recipe_image = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = [
            "id",
            "name",
            "short_description",
            "ingredients",
            "ingredients_list",
            "cooking_time",
            "difficulty",
            "likes",
            "references",
            "recipe_image",
        ]

    def get_ingredients_list(self, obj):
        return obj.return_ingredients_as_list()

    def get_recipe_image(self, obj):
        # Mirror the template app's `media_to_static` filter so API consumers
        # (the Vue SPA) get the same image URLs the Django templates render.
        # All recipe images live under STATIC, which survives Render deploys;
        # MEDIA on free-tier Render is ephemeral.
        url = media_to_static(obj.recipe_image)
        request = self.context.get("request")
        if request is not None:
            return request.build_absolute_uri(url)
        return url


class RecipeSearchStatsSerializer(serializers.Serializer):
    cooking_times = serializers.ListField()
    difficulty_distribution = serializers.DictField()
    ingredient_time_data = serializers.ListField()

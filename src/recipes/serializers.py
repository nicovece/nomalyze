from rest_framework import serializers
from .models import Recipe


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
            "status",
            "likes",
            "references",
            "recipe_image",
        ]

    def get_ingredients_list(self, obj):
        return obj.return_ingredients_as_list()

    def get_recipe_image(self, obj):
        request = self.context.get("request")

        def absolutize(url):
            # R2 returns absolute URLs (https://pub-…r2.dev/...); local FS returns
            # relative URLs (/media/...). Only absolutize the latter.
            if request is not None and url and not url.startswith("http"):
                return request.build_absolute_uri(url)
            return url

        if not obj.recipe_image:
            return None

        return {
            "original": absolutize(obj.recipe_image.url),
            "small": absolutize(obj.image_small.url),
            "medium": absolutize(obj.image_medium.url),
            "large": absolutize(obj.image_large.url),
        }


class RecipeSearchStatsSerializer(serializers.Serializer):
    cooking_times = serializers.ListField()
    difficulty_distribution = serializers.DictField()
    ingredient_time_data = serializers.ListField()

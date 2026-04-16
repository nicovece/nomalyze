from rest_framework import serializers
from .models import Recipe


class RecipeSerializer(serializers.ModelSerializer):
    ingredients_list = serializers.SerializerMethodField()

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


class RecipeSearchStatsSerializer(serializers.Serializer):
    cooking_times = serializers.ListField()
    difficulty_distribution = serializers.DictField()
    ingredient_time_data = serializers.ListField()

from django.db.models import Q
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Recipe
from .serializers import RecipeSerializer, RecipeSearchStatsSerializer


class RecipeListAPIView(generics.ListAPIView):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer


class RecipeDetailAPIView(generics.RetrieveAPIView):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer


def process_wildcard_search(search_term, field):
    """Convert wildcard patterns to Django Q objects for a given field."""
    if not search_term:
        return None

    search_term = search_term.strip()

    if "*" in search_term or "?" in search_term:
        pattern = search_term.replace("*", ".*").replace("?", ".")
        return Q(**{f"{field}__iregex": pattern})
    else:
        return Q(**{f"{field}__icontains": search_term})


class RecipeSearchAPIView(generics.ListAPIView):
    serializer_class = RecipeSerializer

    def get_queryset(self):
        qs = Recipe.objects.all()

        if self.request.query_params.get("show_all") == "true":
            return qs

        name = self.request.query_params.get("name")
        if name:
            name_query = process_wildcard_search(name, "name")
            if name_query:
                qs = qs.filter(name_query)

        ingredients = self.request.query_params.get("ingredients")
        if ingredients:
            for ingredient in [i.strip() for i in ingredients.split(",") if i.strip()]:
                ingredient_query = process_wildcard_search(ingredient, "ingredients")
                if ingredient_query:
                    qs = qs.filter(ingredient_query)

        cooking_time_max = self.request.query_params.get("cooking_time_max")
        if cooking_time_max:
            qs = qs.filter(cooking_time__lte=int(cooking_time_max))

        difficulty = self.request.query_params.get("difficulty")
        if difficulty:
            qs = qs.filter(difficulty=difficulty)

        return qs


class RecipeSearchStatsAPIView(APIView):
    def get(self, request):
        # Reuse the same filtering logic
        search_view = RecipeSearchAPIView()
        search_view.request = request
        search_view.kwargs = {}
        search_view.format_kwarg = None
        qs = search_view.get_queryset()

        cooking_times = [{"name": r.name, "cooking_time": r.cooking_time} for r in qs]

        difficulty_distribution = {}
        for recipe in qs:
            difficulty_distribution[recipe.difficulty] = difficulty_distribution.get(recipe.difficulty, 0) + 1

        ingredient_time_data = [
            {
                "ingredient_count": len(r.return_ingredients_as_list()),
                "cooking_time": r.cooking_time,
            }
            for r in qs
        ]

        serializer = RecipeSearchStatsSerializer(
            {
                "cooking_times": cooking_times,
                "difficulty_distribution": difficulty_distribution,
                "ingredient_time_data": ingredient_time_data,
            }
        )
        return Response(serializer.data)

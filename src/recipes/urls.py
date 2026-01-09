from django.urls import path
from .views import HomeView, RecipeListView, RecipeDetailView, recipe_search

app_name = "recipes"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("recipes/", RecipeListView.as_view(), name="recipe-list"),
    path("recipes/<int:pk>/", RecipeDetailView.as_view(), name="recipe-detail"),
    path("search/", recipe_search, name="recipe-search"),
]

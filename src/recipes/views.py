from django.views.generic import TemplateView, ListView, DetailView
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse
from .models import Recipe
from .forms import RecipeSearchForm
from .utils import get_chart_with_colors
import pandas as pd

def process_wildcard_search(search_term):
    """
    Process wildcard search terms and convert them to Django Q objects
    
    Supports:
    - * wildcards: "pasta*" matches "pasta", "pastas", "pasta-based"
    - ? wildcards: "pasta?" matches "pasta" but not "pastas"
    - Partial matching: "pasta" matches "Pasta al Pesto"
    """
    if not search_term:
        return None
    
    # Remove extra whitespace
    search_term = search_term.strip()
    
    # Handle wildcards
    if '*' in search_term or '?' in search_term:
        # Convert wildcards to regex patterns
        # * becomes .* (any characters)
        # ? becomes . (single character)
        pattern = search_term.replace('*', '.*').replace('?', '.')
        
        # Create Q object for regex matching
        return Q(name__iregex=pattern)
    else:
        # Regular partial matching (case-insensitive)
        return Q(name__icontains=search_term)

class HomeView(TemplateView):
    template_name = 'recipes/home.html'


class RecipeListView(LoginRequiredMixin, ListView):
    model = Recipe
    template_name = 'recipes/list.html'
    context_object_name = 'recipes'

class RecipeDetailView(LoginRequiredMixin, DetailView):
    model = Recipe
    template_name = 'recipes/detail.html'
    context_object_name = 'recipe'


@login_required
def recipe_search(request):
    form = RecipeSearchForm(request.POST or None)
    recipes = None  # Initialize recipes
    charts = None

    if request.method == "POST":
        # Get form data
        search_action = request.POST.get("search_action")
        recipe_name = request.POST.get("recipe_name")
        ingredients = request.POST.get("ingredients")
        cooking_time_max = request.POST.get("cooking_time_max")
        difficulty = request.POST.get("difficulty")

        # Start with all recipes
        qs = Recipe.objects.all()

        # Apply filters only if user clicked "Search & Analyze" (not "Analyze All Recipes")
        if search_action == "search":
            # Apply filters based on form data (AND logic)
            if recipe_name:
                # Use wildcard processing for recipe names
                name_query = process_wildcard_search(recipe_name)
                if name_query:
                    qs = qs.filter(name_query)
            
            if ingredients:
                # Split ingredients by comma and search for each one with wildcard support
                ingredient_list = [ingredient.strip() for ingredient in ingredients.split(",") if ingredient.strip()]
                for ingredient in ingredient_list:
                    if '*' in ingredient or '?' in ingredient:
                        # Handle wildcards in ingredients
                        pattern = ingredient.replace('*', '.*').replace('?', '.')
                        qs = qs.filter(ingredients__iregex=pattern)
                    else:
                        # Regular partial matching for ingredients
                        qs = qs.filter(ingredients__icontains=ingredient)
            
            if cooking_time_max:
                qs = qs.filter(cooking_time__lte=int(cooking_time_max))
            
            if difficulty:
                qs = qs.filter(difficulty=difficulty)
        
        # If search_action == "show_all", no filters are applied (qs remains Recipe.objects.all())

        # Convert QuerySet to list of dictionaries if we have results
        if qs.exists():
            recipes_data = []
            for recipe in qs:
                # Calculate ingredient count
                ingredient_count = len([ing.strip() for ing in recipe.ingredients.split(",") if ing.strip()]) if recipe.ingredients else 0
                
                recipes_data.append({
                    'id': recipe.id,
                    'name': recipe.name,  # Clean name without HTML
                    'cooking_time': recipe.cooking_time,
                    'difficulty': recipe.difficulty,
                    'ingredients': recipe.ingredients,
                    'ingredient_count': ingredient_count,
                    'short_description': recipe.short_description,
                    'recipe_image_url': f'/static/images/{recipe.recipe_image}',
                    'detail_url': f"/recipes/{recipe.id}/"
                })
            
            # Create DataFrame for charts (we still need this for chart generation)
            recipes_df = pd.DataFrame([{
                'id': recipe.id,
                'name': recipe.name,
                'cooking_time': recipe.cooking_time,
                'difficulty': recipe.difficulty,
                'ingredients': recipe.ingredients,
                'ingredient_count': len([ing.strip() for ing in recipe.ingredients.split(",") if ing.strip()]) if recipe.ingredients else 0,
            } for recipe in qs])
            
            # Generate charts with different color schemes
            charts = {
                'bar': get_chart_with_colors('#1', recipes_df, color_scheme='brand'),
                'pie': get_chart_with_colors('#2', recipes_df, color_scheme='brand'),
                'line': get_chart_with_colors('#3', recipes_df, color_scheme='brand')
            }
            
            recipes = recipes_data
            
            # Store search results in session for redirect
            request.session['search_recipes'] = recipes
            request.session['search_charts'] = charts
            request.session['search_form_data'] = {
                'recipe_name': recipe_name,
                'ingredients': ingredients,
                'cooking_time_max': cooking_time_max,
                'difficulty': difficulty
            }
            
            # Redirect to search results section
            return redirect(reverse('recipes:recipe-search') + '#search-results')
        else:
            # Store form data in session for redirect
            request.session['search_form_data'] = {
                'recipe_name': recipe_name,
                'ingredients': ingredients,
                'cooking_time_max': cooking_time_max,
                'difficulty': difficulty
            }
            
            # No results found, redirect to no-results section
            return redirect(reverse('recipes:recipe-search') + '#no-recipes-found')
    
    # Check if we have stored search results from a redirect
    if 'search_recipes' in request.session:
        recipes = request.session.pop('search_recipes')
        charts = request.session.pop('search_charts')
        form_data = request.session.pop('search_form_data', {})
        
        # Pre-populate form with search data
        form = RecipeSearchForm(initial=form_data)

    context = {"form": form, "recipes": recipes, "charts": charts}
    return render(request, "recipes/search.html", context)
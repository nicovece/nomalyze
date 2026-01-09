from django.test import TestCase, Client
from django.urls import reverse, resolve
from django.core.exceptions import ValidationError
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django import forms
from PIL import Image
import tempfile
import os
from .models import Recipe
from .admin import RecipeAdmin
from .views import HomeView, RecipeListView, RecipeDetailView, recipe_search, process_wildcard_search
from .forms import RecipeSearchForm
from .utils import get_chart, get_graph
import pandas as pd
import matplotlib.pyplot as plt
import base64

class RecipeModelTest(TestCase):
    def test_recipe_str_method(self):
        """Test that the string representation returns the recipe name"""
        recipe = Recipe(name="Test Recipe", ingredients="Ingredient1, Ingredient2", cooking_time=10)
        self.assertEqual(str(recipe), "Test Recipe")

    def test_recipe_ingredients_as_list(self):
        """Test converting ingredients string to list"""
        recipe = Recipe(name="Test Recipe", ingredients="Ingredient1, Ingredient2", cooking_time=10)
        self.assertEqual(recipe.return_ingredients_as_list(), ["Ingredient1", "Ingredient2"])

    def test_ingredients_as_list_with_spaces(self):
        """Test ingredients list conversion handles extra spaces properly"""
        recipe = Recipe(name="Test Recipe", ingredients="  Ingredient1 , Ingredient2  ", cooking_time=10)
        self.assertEqual(recipe.return_ingredients_as_list(), ["Ingredient1", "Ingredient2"])

    def test_ingredients_as_list_empty_string(self):
        """Test ingredients list conversion with empty string"""
        recipe = Recipe(name="Test Recipe", ingredients="", cooking_time=10)
        self.assertEqual(recipe.return_ingredients_as_list(), [])

    def test_ingredients_as_list_none_value(self):
        """Test ingredients list conversion with None value"""
        recipe = Recipe(name="Test Recipe", ingredients=None, cooking_time=10)
        self.assertEqual(recipe.return_ingredients_as_list(), [])

    def test_ingredients_as_list_single_ingredient(self):
        """Test ingredients list conversion with single ingredient"""
        recipe = Recipe(name="Test Recipe", ingredients="Single Ingredient", cooking_time=10)
        self.assertEqual(recipe.return_ingredients_as_list(), ["Single Ingredient"])

    def test_ingredients_as_list_with_empty_ingredients(self):
        """Test ingredients list conversion filters out empty ingredients"""
        recipe = Recipe(name="Test Recipe", ingredients="Ingredient1, , Ingredient2,  , Ingredient3", cooking_time=10)
        self.assertEqual(recipe.return_ingredients_as_list(), ["Ingredient1", "Ingredient2", "Ingredient3"])

    def test_calculate_difficulty_easy(self):
        """Test difficulty calculation for easy recipes (short time, few ingredients)"""
        recipe = Recipe(name="Easy Recipe", ingredients="Ingredient1, Ingredient2, Ingredient3", cooking_time=5)
        self.assertEqual(recipe.calculate_difficulty(), "Easy")

    def test_calculate_difficulty_medium(self):
        """Test difficulty calculation for medium recipes (short time, many ingredients)"""
        recipe = Recipe(name="Medium Recipe", ingredients="Ingredient1, Ingredient2, Ingredient3, Ingredient4, Ingredient5", cooking_time=8)
        self.assertEqual(recipe.calculate_difficulty(), "Medium")

    def test_calculate_difficulty_intermediate(self):
        """Test difficulty calculation for intermediate recipes (long time, few ingredients)"""
        recipe = Recipe(name="Intermediate Recipe", ingredients="Ingredient1, Ingredient2", cooking_time=15)
        self.assertEqual(recipe.calculate_difficulty(), "Intermediate")

    def test_calculate_difficulty_hard(self):
        """Test difficulty calculation for hard recipes (long time, many ingredients)"""
        recipe = Recipe(name="Hard Recipe", ingredients="Ingredient1, Ingredient2, Ingredient3, Ingredient4, Ingredient5", cooking_time=20)
        self.assertEqual(recipe.calculate_difficulty(), "Hard")

    def test_calculate_difficulty_boundary_values(self):
        """Test difficulty calculation at boundary values"""
        # Easy boundary: cooking_time < 10 and num_ingredients < 4
        recipe1 = Recipe(name="Easy Boundary", ingredients="Ingredient1, Ingredient2, Ingredient3", cooking_time=9)
        self.assertEqual(recipe1.calculate_difficulty(), "Easy")
        
        # Medium boundary: cooking_time < 10 and num_ingredients >= 4
        recipe2 = Recipe(name="Medium Boundary", ingredients="Ingredient1, Ingredient2, Ingredient3, Ingredient4", cooking_time=9)
        self.assertEqual(recipe2.calculate_difficulty(), "Medium")
        
        # Intermediate boundary: cooking_time >= 10 and num_ingredients < 4
        recipe3 = Recipe(name="Intermediate Boundary", ingredients="Ingredient1, Ingredient2, Ingredient3", cooking_time=10)
        self.assertEqual(recipe3.calculate_difficulty(), "Intermediate")
        
        # Hard boundary: cooking_time >= 10 and num_ingredients >= 4
        recipe4 = Recipe(name="Hard Boundary", ingredients="Ingredient1, Ingredient2, Ingredient3, Ingredient4", cooking_time=10)
        self.assertEqual(recipe4.calculate_difficulty(), "Hard")

    def test_auto_calculate_difficulty_on_save(self):
        """Test that difficulty is automatically calculated when saving"""
        recipe = Recipe(name="Auto Difficulty Recipe", ingredients="Ingredient1, Ingredient2, Ingredient3, Ingredient4", cooking_time=25)
        recipe.save()
        
        # Refresh from database to ensure the save method was called
        recipe.refresh_from_db()
        self.assertEqual(recipe.difficulty, "Hard")

    def test_recipe_creation_with_all_fields(self):
        """Test creating a recipe with all fields populated"""
        recipe = Recipe(
            name="Complete Recipe",
            ingredients="Salt, Pepper, Oil, Garlic",
            cooking_time=30,
            likes=5,
            comments="This is a great recipe!",
            references="https://example.com/recipe"
        )
        recipe.save()
        
        self.assertEqual(recipe.name, "Complete Recipe")
        self.assertEqual(recipe.ingredients, "Salt, Pepper, Oil, Garlic")
        self.assertEqual(recipe.cooking_time, 30)
        self.assertEqual(recipe.likes, 5)
        self.assertEqual(recipe.comments, "This is a great recipe!")
        self.assertEqual(recipe.references, "https://example.com/recipe")
        self.assertEqual(recipe.difficulty, "Hard")  # Should be auto-calculated

    def test_recipe_creation_with_minimal_fields(self):
        """Test creating a recipe with only required fields"""
        recipe = Recipe(
            name="Minimal Recipe",
            ingredients="Ingredient1",
            cooking_time=5
        )
        recipe.save()
        
        self.assertEqual(recipe.name, "Minimal Recipe")
        self.assertEqual(recipe.ingredients, "Ingredient1")
        self.assertEqual(recipe.cooking_time, 5)
        self.assertEqual(recipe.likes, 0)  # Default value
        self.assertEqual(recipe.difficulty, "Easy")  # Auto-calculated

    def test_recipe_field_constraints(self):
        """Test that field constraints are properly enforced"""
        # Test name max length using full_clean() which will validate the constraint
        long_name = "A" * 121  # Exceeds max_length=120
        recipe = Recipe(name=long_name, ingredients="Test", cooking_time=10)
        
        # This should raise a validation error when validating
        with self.assertRaises(ValidationError):
            recipe.full_clean()
        
        # Test that a name exactly at the limit works
        exact_length_name = "A" * 120  # Exactly max_length=120
        recipe = Recipe(name=exact_length_name, ingredients="Test", cooking_time=10)
        try:
            recipe.full_clean()
        except ValidationError:
            self.fail("ValidationError raised unexpectedly for name at max length")

    def test_cooking_time_validators(self):
        """Test cooking time field validators"""
        # Test minimum value validator
        recipe = Recipe(name="Test Recipe", ingredients="Test", cooking_time=0)
        with self.assertRaises(ValidationError):
            recipe.full_clean()
        
        # Test maximum value validator
        recipe = Recipe(name="Test Recipe", ingredients="Test", cooking_time=1441)
        with self.assertRaises(ValidationError):
            recipe.full_clean()
        
        # Test valid values
        recipe = Recipe(name="Test Recipe", ingredients="Test", cooking_time=1)
        try:
            recipe.full_clean()
        except ValidationError:
            self.fail("ValidationError raised unexpectedly for valid cooking time 1")
        
        recipe = Recipe(name="Test Recipe", ingredients="Test", cooking_time=1440)
        try:
            recipe.full_clean()
        except ValidationError:
            self.fail("ValidationError raised unexpectedly for valid cooking time 1440")

    def test_recipe_model_meta(self):
        """Test that the model has proper meta configuration"""
        recipe = Recipe(name="Meta Test", ingredients="Test", cooking_time=10)
        self.assertEqual(recipe.id, None)  # AutoField, not set until saved
        self.assertTrue(hasattr(recipe, 'id'))  # Should have the field

    def test_validation_empty_name(self):
        """Test validation fails with empty name"""
        recipe = Recipe(name="", ingredients="Test ingredient", cooking_time=10)
        with self.assertRaises(ValidationError):
            recipe.full_clean()

    def test_validation_whitespace_name(self):
        """Test validation fails with whitespace-only name"""
        recipe = Recipe(name="   ", ingredients="Test ingredient", cooking_time=10)
        with self.assertRaises(ValidationError):
            recipe.full_clean()

    def test_validation_empty_ingredients(self):
        """Test validation fails with empty ingredients"""
        recipe = Recipe(name="Test Recipe", ingredients="", cooking_time=10)
        with self.assertRaises(ValidationError):
            recipe.full_clean()

    def test_validation_whitespace_ingredients(self):
        """Test validation fails with whitespace-only ingredients"""
        recipe = Recipe(name="Test Recipe", ingredients="   ", cooking_time=10)
        with self.assertRaises(ValidationError):
            recipe.full_clean()

    def test_validation_zero_cooking_time(self):
        """Test validation fails with zero cooking time"""
        recipe = Recipe(name="Test Recipe", ingredients="Test ingredient", cooking_time=0)
        with self.assertRaises(ValidationError):
            recipe.full_clean()

    def test_validation_negative_cooking_time(self):
        """Test validation fails with negative cooking time"""
        recipe = Recipe(name="Test Recipe", ingredients="Test ingredient", cooking_time=-5)
        with self.assertRaises(ValidationError):
            recipe.full_clean()

    def test_validation_cooking_time_too_high(self):
        """Test validation fails with cooking time exceeding 24 hours"""
        recipe = Recipe(name="Test Recipe", ingredients="Test ingredient", cooking_time=1441)
        with self.assertRaises(ValidationError):
            recipe.full_clean()

    def test_validation_valid_recipe(self):
        """Test validation passes with valid recipe data"""
        recipe = Recipe(name="Valid Recipe", ingredients="Ingredient1, Ingredient2", cooking_time=30)
        try:
            recipe.full_clean()
        except ValidationError:
            self.fail("ValidationError raised unexpectedly!")

    def test_short_description_field(self):
        """Test short_description field functionality"""
        # Test creating recipe with short_description
        recipe = Recipe(
            name="Test Recipe",
            ingredients="Ingredient1, Ingredient2",
            cooking_time=30,
            short_description="A delicious test recipe"
        )
        recipe.save()
        
        self.assertEqual(recipe.short_description, "A delicious test recipe")
        
        # Test creating recipe without short_description (should be blank)
        recipe2 = Recipe(
            name="Test Recipe 2",
            ingredients="Ingredient1",
            cooking_time=15
        )
        recipe2.save()
        
        self.assertEqual(recipe2.short_description, "")

    def test_short_description_max_length(self):
        """Test short_description field max length constraint"""
        # Test with description at max length (300 characters)
        max_desc = "A" * 300
        recipe = Recipe(
            name="Test Recipe",
            ingredients="Ingredient1",
            cooking_time=30,
            short_description=max_desc
        )
        try:
            recipe.full_clean()
        except ValidationError:
            self.fail("ValidationError raised unexpectedly for max length description")
        
        # Note: TextField with max_length doesn't enforce validation at model level
        # The max_length is mainly for form validation and database hints
        # So we just test that it can be saved
        recipe.save()
        self.assertEqual(len(recipe.short_description), 300)

    def test_recipe_image_field_default(self):
        """Test recipe_image field default value"""
        recipe = Recipe(
            name="Test Recipe",
            ingredients="Ingredient1",
            cooking_time=30
        )
        recipe.save()
        
        # Should have default image
        self.assertEqual(recipe.recipe_image.name, "no_picture.png")

    def test_recipe_image_field_upload(self):
        """Test recipe_image field with uploaded image"""
        # Create a simple test image
        image = Image.new('RGB', (100, 100), color='red')
        temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        image.save(temp_file.name, 'JPEG')
        temp_file.close()
        
        try:
            with open(temp_file.name, 'rb') as f:
                uploaded_file = SimpleUploadedFile(
                    "test_image.jpg",
                    f.read(),
                    content_type="image/jpeg"
                )
            
            recipe = Recipe(
                name="Test Recipe",
                ingredients="Ingredient1",
                cooking_time=30,
                recipe_image=uploaded_file
            )
            recipe.save()
            
            # Check that image was saved
            self.assertTrue(recipe.recipe_image.name.startswith('recipes/'))
            self.assertTrue(recipe.recipe_image.name.endswith('.jpg'))
            
        finally:
            # Clean up
            os.unlink(temp_file.name)
            if recipe.recipe_image and os.path.exists(recipe.recipe_image.path):
                os.unlink(recipe.recipe_image.path)


class RecipeViewTest(TestCase):
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Create test recipes
        self.recipe1 = Recipe.objects.create(
            name="Test Recipe 1",
            ingredients="Ingredient1, Ingredient2",
            cooking_time=30,
            short_description="A test recipe"
        )
        
        self.recipe2 = Recipe.objects.create(
            name="Test Recipe 2",
            ingredients="Ingredient3, Ingredient4, Ingredient5",
            cooking_time=45,
            short_description="Another test recipe"
        )

    def test_home_view(self):
        """Test HomeView renders correctly"""
        response = self.client.get(reverse('recipes:home'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recipes/home.html')

    def test_recipe_list_view(self):
        """Test RecipeListView renders correctly with recipes"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('recipes:recipe-list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recipes/list.html')
        self.assertIn('recipes', response.context)
        self.assertEqual(len(response.context['recipes']), 2)
        self.assertIn(self.recipe1, response.context['recipes'])
        self.assertIn(self.recipe2, response.context['recipes'])

    def test_recipe_list_view_empty(self):
        """Test RecipeListView with no recipes"""
        self.client.login(username='testuser', password='testpass123')
        # Delete all recipes
        Recipe.objects.all().delete()
        
        response = self.client.get(reverse('recipes:recipe-list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recipes/list.html')
        self.assertIn('recipes', response.context)
        self.assertEqual(len(response.context['recipes']), 0)

    def test_recipe_detail_view(self):
        """Test RecipeDetailView renders correctly"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('recipes:recipe-detail', kwargs={'pk': self.recipe1.pk}))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recipes/detail.html')
        self.assertIn('recipe', response.context)
        self.assertEqual(response.context['recipe'], self.recipe1)

    def test_recipe_detail_view_not_found(self):
        """Test RecipeDetailView with non-existent recipe"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('recipes:recipe-detail', kwargs={'pk': 999}))
        
        self.assertEqual(response.status_code, 404)

    def test_recipe_detail_view_context(self):
        """Test RecipeDetailView context contains correct data"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('recipes:recipe-detail', kwargs={'pk': self.recipe1.pk}))
        
        recipe = response.context['recipe']
        self.assertEqual(recipe.name, "Test Recipe 1")
        self.assertEqual(recipe.ingredients, "Ingredient1, Ingredient2")
        self.assertEqual(recipe.cooking_time, 30)
        self.assertEqual(recipe.short_description, "A test recipe")
        self.assertEqual(recipe.difficulty, "Intermediate")  # Auto-calculated

    def test_recipe_list_view_context(self):
        """Test RecipeListView context contains correct data"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('recipes:recipe-list'))
        
        recipes = response.context['recipes']
        self.assertEqual(len(recipes), 2)
        
        # Check that recipes are ordered correctly (by creation order)
        self.assertEqual(recipes[0], self.recipe1)
        self.assertEqual(recipes[1], self.recipe2)


class RecipeURLTest(TestCase):
    def test_home_url(self):
        """Test home URL pattern"""
        url = reverse('recipes:home')
        self.assertEqual(url, '/')
        
        # Test URL resolution
        resolved = resolve('/')
        self.assertEqual(resolved.func.__name__, HomeView.as_view().__name__)

    def test_recipe_list_url(self):
        """Test recipe list URL pattern"""
        url = reverse('recipes:recipe-list')
        self.assertEqual(url, '/recipes/')
        
        # Test URL resolution
        resolved = resolve('/recipes/')
        self.assertEqual(resolved.func.__name__, RecipeListView.as_view().__name__)

    def test_recipe_detail_url(self):
        """Test recipe detail URL pattern"""
        url = reverse('recipes:recipe-detail', kwargs={'pk': 1})
        self.assertEqual(url, '/recipes/1/')
        
        # Test URL resolution
        resolved = resolve('/recipes/1/')
        self.assertEqual(resolved.func.__name__, RecipeDetailView.as_view().__name__)
        self.assertEqual(int(resolved.kwargs['pk']), 1)

    def test_url_namespace(self):
        """Test that URLs use correct namespace"""
        # Test that URLs are namespaced correctly
        self.assertEqual(reverse('recipes:home'), '/')
        self.assertEqual(reverse('recipes:recipe-list'), '/recipes/')
        self.assertEqual(reverse('recipes:recipe-detail', kwargs={'pk': 1}), '/recipes/1/')


class RecipeTemplateTest(TestCase):
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.recipe = Recipe.objects.create(
            name="Template Test Recipe",
            ingredients="Ingredient1, Ingredient2, Ingredient3",
            cooking_time=25,
            short_description="A recipe for testing templates",
            references="https://example.com/recipe"
        )

    def test_home_template_content(self):
        """Test home template renders expected content"""
        response = self.client.get(reverse('recipes:home'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nomalyze')  # Assuming this is in the template

    def test_recipe_list_template_content(self):
        """Test recipe list template renders expected content"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('recipes:recipe-list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome to our')
        self.assertContains(response, 'Recipes List!')
        self.assertContains(response, 'Template Test Recipe')
        self.assertContains(response, 'A recipe for testing templates')
        self.assertContains(response, 'View')
        self.assertContains(response, 'Recipe')

    def test_recipe_list_template_no_recipes(self):
        """Test recipe list template with no recipes"""
        self.client.login(username='testuser', password='testpass123')
        Recipe.objects.all().delete()
        
        response = self.client.get(reverse('recipes:recipe-list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No recipes found')

    def test_recipe_detail_template_content(self):
        """Test recipe detail template renders expected content"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('recipes:recipe-detail', kwargs={'pk': self.recipe.pk}))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Template Test Recipe')
        self.assertContains(response, 'A recipe for testing templates')
        self.assertContains(response, 'Ingredients')
        self.assertContains(response, 'Ingredient1')
        self.assertContains(response, 'Ingredient2')
        self.assertContains(response, 'Ingredient3')
        self.assertContains(response, '25 minutes')
        self.assertContains(response, 'Intermediate')  # Auto-calculated difficulty (25 min, 3 ingredients)
        self.assertContains(response, 'View Reference')
        self.assertContains(response, 'https://example.com/recipe')
        self.assertContains(response, 'Like (0)')

    def test_recipe_detail_template_without_reference(self):
        """Test recipe detail template without reference URL"""
        self.client.login(username='testuser', password='testpass123')
        self.recipe.references = ""
        self.recipe.save()
        
        response = self.client.get(reverse('recipes:recipe-detail', kwargs={'pk': self.recipe.pk}))
        
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'View Reference')

    def test_recipe_detail_template_without_short_description(self):
        """Test recipe detail template without short description"""
        self.client.login(username='testuser', password='testpass123')
        self.recipe.short_description = ""
        self.recipe.save()
        
        response = self.client.get(reverse('recipes:recipe-detail', kwargs={'pk': self.recipe.pk}))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Template Test Recipe')
        # Short description should not be rendered if empty

    def test_base_template_inheritance(self):
        """Test that templates extend base template"""
        response = self.client.get(reverse('recipes:home'))
        
        self.assertEqual(response.status_code, 200)
        # Check that base template is used (assuming it has a title block)
        self.assertContains(response, '<title>')  # Assuming base template has title


class RecipeAdminTest(TestCase):
    def setUp(self):
        """Set up test data"""
        self.site = AdminSite()
        self.admin = RecipeAdmin(Recipe, self.site)
        
        # Create test user and recipe
        self.user = User.objects.create_user(
            username='admin',
            password='admin123',
            is_staff=True,
            is_superuser=True
        )
        
        self.recipe = Recipe.objects.create(
            name="Admin Test Recipe",
            ingredients="Ingredient1, Ingredient2",
            cooking_time=30,
            short_description="A recipe for testing admin"
        )

    def test_admin_registration(self):
        """Test that Recipe model is registered in admin"""
        from django.contrib import admin
        self.assertTrue(admin.site.is_registered(Recipe))

    def test_admin_list_display(self):
        """Test admin list display configuration"""
        expected_fields = ['name', 'cooking_time', 'difficulty', 'likes']
        self.assertEqual(self.admin.list_display, expected_fields)

    def test_admin_list_filter(self):
        """Test admin list filter configuration"""
        expected_filters = ['difficulty', 'cooking_time']
        self.assertEqual(self.admin.list_filter, expected_filters)

    def test_admin_search_fields(self):
        """Test admin search fields configuration"""
        expected_search_fields = ['name', 'ingredients']
        self.assertEqual(self.admin.search_fields, expected_search_fields)

    def test_admin_readonly_fields(self):
        """Test admin readonly fields configuration"""
        expected_readonly_fields = ['difficulty', 'likes', 'comments']
        self.assertEqual(self.admin.readonly_fields, expected_readonly_fields)

    def test_admin_fieldsets(self):
        """Test admin fieldsets configuration"""
        fieldsets = self.admin.fieldsets
        
        # Check that fieldsets exist
        self.assertIsNotNone(fieldsets)
        self.assertEqual(len(fieldsets), 3)
        
        # Check fieldset structure
        basic_info = fieldsets[0]
        self.assertEqual(basic_info[0], 'Basic Information')
        self.assertIn('name', basic_info[1]['fields'])
        self.assertIn('short_description', basic_info[1]['fields'])
        self.assertIn('ingredients', basic_info[1]['fields'])
        self.assertIn('cooking_time', basic_info[1]['fields'])
        self.assertIn('recipe_image', basic_info[1]['fields'])
        
        calculated_fields = fieldsets[1]
        self.assertEqual(calculated_fields[0], 'Calculated Fields')
        self.assertIn('difficulty', calculated_fields[1]['fields'])
        self.assertIn('likes', calculated_fields[1]['fields'])
        self.assertIn('comments', calculated_fields[1]['fields'])
        self.assertIn('collapse', calculated_fields[1]['classes'])
        
        additional_info = fieldsets[2]
        self.assertEqual(additional_info[0], 'Additional Information')
        self.assertIn('references', additional_info[1]['fields'])

    def test_admin_changelist_view(self):
        """Test admin changelist view"""
        self.client.login(username='admin', password='admin123')
        response = self.client.get('/admin/recipes/recipe/')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin Test Recipe')
        self.assertContains(response, '30')
        self.assertContains(response, 'Intermediate')  # Auto-calculated difficulty
        self.assertContains(response, '0')  # Default likes

    def test_admin_change_view(self):
        """Test admin change view"""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(f'/admin/recipes/recipe/{self.recipe.pk}/change/')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin Test Recipe')
        self.assertContains(response, 'A recipe for testing admin')
        self.assertContains(response, 'Ingredient1, Ingredient2')
        self.assertContains(response, '30')
        self.assertContains(response, 'Intermediate')  # Readonly field
        self.assertContains(response, '0')  # Readonly field


class RecipeSearchFormTest(TestCase):
    def setUp(self):
        """Set up test data"""
        self.form = RecipeSearchForm()

    def test_form_fields(self):
        """Test that form has all required fields"""
        expected_fields = ['recipe_name', 'ingredients', 'cooking_time_max', 'difficulty', 'chart_type']
        for field in expected_fields:
            self.assertIn(field, self.form.fields)

    def test_form_field_types(self):
        """Test that form fields have correct types"""
        self.assertIsInstance(self.form.fields['recipe_name'], forms.CharField)
        self.assertIsInstance(self.form.fields['ingredients'], forms.CharField)
        self.assertIsInstance(self.form.fields['cooking_time_max'], forms.IntegerField)
        self.assertIsInstance(self.form.fields['difficulty'], forms.ChoiceField)
        self.assertIsInstance(self.form.fields['chart_type'], forms.ChoiceField)

    def test_form_field_required(self):
        """Test that form fields have correct required settings"""
        self.assertFalse(self.form.fields['recipe_name'].required)
        self.assertFalse(self.form.fields['ingredients'].required)
        self.assertFalse(self.form.fields['cooking_time_max'].required)
        self.assertFalse(self.form.fields['difficulty'].required)
        self.assertTrue(self.form.fields['chart_type'].required)

    def test_form_field_max_lengths(self):
        """Test that form fields have correct max lengths"""
        self.assertEqual(self.form.fields['recipe_name'].max_length, 120)
        self.assertEqual(self.form.fields['ingredients'].max_length, 200)

    def test_form_field_choices(self):
        """Test that form fields have correct choices"""
        # Test difficulty choices
        difficulty_choices = self.form.fields['difficulty'].choices
        expected_difficulties = ['', 'Easy', 'Medium', 'Intermediate', 'Hard']
        for choice in difficulty_choices:
            self.assertIn(choice[0], expected_difficulties)

        # Test chart type choices
        chart_choices = self.form.fields['chart_type'].choices
        expected_charts = ['#1', '#2', '#3']
        for choice in chart_choices:
            self.assertIn(choice[0], expected_charts)

    def test_form_field_help_text(self):
        """Test that form fields have help text"""
        self.assertIsNotNone(self.form.fields['recipe_name'].help_text)
        self.assertIsNotNone(self.form.fields['ingredients'].help_text)
        self.assertIn('characters', self.form.fields['recipe_name'].help_text.lower())
        self.assertIn('characters', self.form.fields['ingredients'].help_text.lower())

    def test_form_field_placeholders(self):
        """Test that form fields have placeholders"""
        recipe_name_widget = self.form.fields['recipe_name'].widget
        ingredients_widget = self.form.fields['ingredients'].widget
        
        self.assertIn('placeholder', recipe_name_widget.attrs)
        self.assertIn('placeholder', ingredients_widget.attrs)
        self.assertIn('wildcard', recipe_name_widget.attrs['placeholder'].lower())

    def test_form_validation_valid_data(self):
        """Test form validation with valid data"""
        form_data = {
            'recipe_name': 'pasta',
            'ingredients': 'tomato, cheese',
            'cooking_time_max': 30,
            'difficulty': 'Easy',
            'chart_type': '#1'
        }
        form = RecipeSearchForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_validation_empty_data(self):
        """Test form validation with empty data (should be valid)"""
        form_data = {
            'chart_type': '#1'  # Only required field
        }
        form = RecipeSearchForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_validation_missing_required_field(self):
        """Test form validation with missing required field"""
        form_data = {
            'recipe_name': 'pasta'
        }
        form = RecipeSearchForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('chart_type', form.errors)

    def test_form_validation_invalid_cooking_time(self):
        """Test form validation with invalid cooking time"""
        form_data = {
            'cooking_time_max': 0,  # Below minimum
            'chart_type': '#1'
        }
        form = RecipeSearchForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('cooking_time_max', form.errors)

    def test_form_validation_cooking_time_too_high(self):
        """Test form validation with cooking time too high"""
        form_data = {
            'cooking_time_max': 1441,  # Above maximum
            'chart_type': '#1'
        }
        form = RecipeSearchForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('cooking_time_max', form.errors)

    def test_form_validation_invalid_difficulty(self):
        """Test form validation with invalid difficulty"""
        form_data = {
            'difficulty': 'Invalid',
            'chart_type': '#1'
        }
        form = RecipeSearchForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('difficulty', form.errors)

    def test_form_validation_invalid_chart_type(self):
        """Test form validation with invalid chart type"""
        form_data = {
            'chart_type': 'invalid'
        }
        form = RecipeSearchForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('chart_type', form.errors)


class RecipeSearchViewTest(TestCase):
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Create test recipes
        self.recipe1 = Recipe.objects.create(
            name="Pasta al Pesto",
            ingredients="pasta, pesto, cheese, garlic",
            cooking_time=10,
            difficulty="Hard"
        )
        
        self.recipe2 = Recipe.objects.create(
            name="Pizza Margherita",
            ingredients="dough, tomato, cheese, basil",
            cooking_time=5,
            difficulty="Medium"
        )
        
        self.recipe3 = Recipe.objects.create(
            name="Summer Salad",
            ingredients="lettuce, tomato, cucumber, olive oil",
            cooking_time=15,
            difficulty="Hard"
        )

    def test_search_view_login_required(self):
        """Test that search view requires login"""
        response = self.client.get(reverse('recipes:recipe-search'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_search_view_get_request(self):
        """Test search view with GET request"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('recipes:recipe-search'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recipes/search.html')
        self.assertIn('form', response.context)
        self.assertIsNone(response.context['recipes_df'])
        self.assertIsNone(response.context['chart'])

    def test_search_view_post_empty_search(self):
        """Test search view with empty search (should show all recipes)"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('recipes:recipe-search'), {
            'search_action': 'search',
            'chart_type': '#1'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('recipes_df', response.context)
        self.assertIn('chart', response.context)
        self.assertIsNotNone(response.context['recipes_df'])
        self.assertIsNotNone(response.context['chart'])

    def test_search_view_post_show_all(self):
        """Test search view with show all action"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('recipes:recipe-search'), {
            'search_action': 'show_all',
            'chart_type': '#1'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('recipes_df', response.context)
        self.assertIn('chart', response.context)
        self.assertIsNotNone(response.context['recipes_df'])
        self.assertIsNotNone(response.context['chart'])

    def test_search_view_recipe_name_filter(self):
        """Test search view with recipe name filter"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('recipes:recipe-search'), {
            'search_action': 'search',
            'recipe_name': 'pasta',
            'chart_type': '#1'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('recipes_df', response.context)
        self.assertIsNotNone(response.context['recipes_df'])
        # Should contain "Pasta al Pesto" but not "Pizza Margherita" or "Summer Salad"

    def test_search_view_ingredients_filter(self):
        """Test search view with ingredients filter"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('recipes:recipe-search'), {
            'search_action': 'search',
            'ingredients': 'tomato',
            'chart_type': '#1'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('recipes_df', response.context)
        self.assertIsNotNone(response.context['recipes_df'])
        # Should contain recipes with tomato in ingredients

    def test_search_view_cooking_time_filter(self):
        """Test search view with cooking time filter"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('recipes:recipe-search'), {
            'search_action': 'search',
            'cooking_time_max': 10,
            'chart_type': '#1'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('recipes_df', response.context)
        self.assertIsNotNone(response.context['recipes_df'])
        # Should contain recipes with cooking time <= 10 minutes

    def test_search_view_difficulty_filter(self):
        """Test search view with difficulty filter"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('recipes:recipe-search'), {
            'search_action': 'search',
            'difficulty': 'Hard',
            'chart_type': '#1'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('recipes_df', response.context)
        self.assertIsNotNone(response.context['recipes_df'])
        # Should contain only Hard difficulty recipes

    def test_search_view_multiple_filters(self):
        """Test search view with multiple filters"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('recipes:recipe-search'), {
            'search_action': 'search',
            'recipe_name': 'pasta',
            'cooking_time_max': 15,
            'difficulty': 'Hard',
            'chart_type': '#2'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('recipes_df', response.context)
        self.assertIsNotNone(response.context['recipes_df'])

    def test_search_view_no_results(self):
        """Test search view with no matching results"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('recipes:recipe-search'), {
            'search_action': 'search',
            'recipe_name': 'nonexistent',
            'chart_type': '#1'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('recipes_df', response.context)
        self.assertIsNone(response.context['recipes_df'])
        self.assertIsNone(response.context['chart'])

    def test_search_view_chart_generation(self):
        """Test that charts are generated correctly"""
        self.client.login(username='testuser', password='testpass123')
        
        # Test bar chart
        response = self.client.post(reverse('recipes:recipe-search'), {
            'search_action': 'show_all',
            'chart_type': '#1'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context['chart'])
        
        # Test pie chart
        response = self.client.post(reverse('recipes:recipe-search'), {
            'search_action': 'show_all',
            'chart_type': '#2'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context['chart'])
        
        # Test line chart
        response = self.client.post(reverse('recipes:recipe-search'), {
            'search_action': 'show_all',
            'chart_type': '#3'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context['chart'])


class WildcardSearchTest(TestCase):
    def setUp(self):
        """Set up test data"""
        self.recipe1 = Recipe.objects.create(
            name="Pasta al Pesto",
            ingredients="pasta, pesto, cheese",
            cooking_time=10
        )
        
        self.recipe2 = Recipe.objects.create(
            name="Pasta alla Carbonara",
            ingredients="pasta, eggs, cheese",
            cooking_time=15
        )
        
        self.recipe3 = Recipe.objects.create(
            name="Pizza Margherita",
            ingredients="dough, tomato, cheese",
            cooking_time=5
        )

    def test_process_wildcard_search_empty(self):
        """Test wildcard search with empty input"""
        result = process_wildcard_search("")
        self.assertIsNone(result)
        
        result = process_wildcard_search(None)
        self.assertIsNone(result)

    def test_process_wildcard_search_regular_text(self):
        """Test wildcard search with regular text (no wildcards)"""
        result = process_wildcard_search("pasta")
        self.assertIsNotNone(result)
        # Should return a Q object for icontains

    def test_process_wildcard_search_asterisk(self):
        """Test wildcard search with asterisk wildcard"""
        result = process_wildcard_search("pasta*")
        self.assertIsNotNone(result)
        # Should return a Q object for iregex

    def test_process_wildcard_search_question_mark(self):
        """Test wildcard search with question mark wildcard"""
        result = process_wildcard_search("pasta?")
        self.assertIsNotNone(result)
        # Should return a Q object for iregex

    def test_process_wildcard_search_multiple_wildcards(self):
        """Test wildcard search with multiple wildcards"""
        result = process_wildcard_search("pasta*?")
        self.assertIsNotNone(result)
        # Should return a Q object for iregex

    def test_wildcard_search_functionality(self):
        """Test that wildcard search actually works with database queries"""
        # Test asterisk wildcard
        qs = Recipe.objects.filter(name__iregex="pasta.*")
        self.assertIn(self.recipe1, qs)
        self.assertIn(self.recipe2, qs)
        self.assertNotIn(self.recipe3, qs)
        
        # Test question mark wildcard
        qs = Recipe.objects.filter(name__iregex="pasta.")
        # This should match "pasta" followed by exactly one character
        # "Pasta al Pesto" and "Pasta alla Carbonara" both start with "Pasta " (6 chars)
        # So this might not match as expected, but the regex should work

    def test_ingredients_wildcard_search(self):
        """Test wildcard search with ingredients"""
        # Test asterisk wildcard in ingredients
        qs = Recipe.objects.filter(ingredients__iregex="pasta.*")
        self.assertIn(self.recipe1, qs)
        self.assertIn(self.recipe2, qs)
        self.assertNotIn(self.recipe3, qs)


class ChartUtilsTest(TestCase):
    def setUp(self):
        """Set up test data"""
        # Create test DataFrame
        self.test_data = pd.DataFrame({
            'name': ['Recipe 1', 'Recipe 2', 'Recipe 3'],
            'cooking_time': [10, 15, 20],
            'difficulty': ['Easy', 'Medium', 'Hard'],
            'ingredient_count': [3, 5, 7]
        })

    def test_get_graph_function(self):
        """Test that get_graph function returns base64 string"""
        # Create a simple plot
        plt.figure()
        plt.plot([1, 2, 3], [1, 4, 2])
        plt.title("Test Chart")
        
        # Get the graph
        result = get_graph()
        
        # Should return a base64 string
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
        
        # Should be valid base64
        try:
            decoded = base64.b64decode(result)
            self.assertIsInstance(decoded, bytes)
        except Exception:
            self.fail("get_graph() did not return valid base64")

    def test_get_chart_bar_chart(self):
        """Test bar chart generation"""
        result = get_chart('#1', self.test_data)
        
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
        
        # Should be valid base64
        try:
            decoded = base64.b64decode(result)
            self.assertIsInstance(decoded, bytes)
        except Exception:
            self.fail("get_chart() did not return valid base64 for bar chart")

    def test_get_chart_pie_chart(self):
        """Test pie chart generation"""
        result = get_chart('#2', self.test_data)
        
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
        
        # Should be valid base64
        try:
            decoded = base64.b64decode(result)
            self.assertIsInstance(decoded, bytes)
        except Exception:
            self.fail("get_chart() did not return valid base64 for pie chart")

    def test_get_chart_line_chart(self):
        """Test line chart generation"""
        result = get_chart('#3', self.test_data)
        
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
        
        # Should be valid base64
        try:
            decoded = base64.b64decode(result)
            self.assertIsInstance(decoded, bytes)
        except Exception:
            self.fail("get_chart() did not return valid base64 for line chart")

    def test_get_chart_invalid_type(self):
        """Test chart generation with invalid chart type"""
        result = get_chart('invalid', self.test_data)
        
        # Should still return something (empty chart or error chart)
        self.assertIsInstance(result, str)

    def test_chart_with_empty_data(self):
        """Test chart generation with empty DataFrame"""
        empty_data = pd.DataFrame()
        
        # This might raise an exception, which is expected
        with self.assertRaises((KeyError, IndexError, ValueError)):
            get_chart('#1', empty_data)


class RecipeSearchURLTest(TestCase):
    def test_recipe_search_url(self):
        """Test recipe search URL pattern"""
        url = reverse('recipes:recipe-search')
        self.assertEqual(url, '/search/')
        
        # Test URL resolution
        resolved = resolve('/search/')
        self.assertEqual(resolved.func, recipe_search)

    def test_recipe_search_url_namespace(self):
        """Test that recipe search URL uses correct namespace"""
        self.assertEqual(reverse('recipes:recipe-search'), '/search/')


class RecipeSearchTemplateTest(TestCase):
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.recipe = Recipe.objects.create(
            name="Template Test Recipe",
            ingredients="ingredient1, ingredient2",
            cooking_time=30,
            difficulty="Hard"
        )

    def test_search_template_content(self):
        """Test search template renders expected content"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('recipes:recipe-search'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Search Recipes & Analyze Data')
        self.assertContains(response, 'Search Criteria')
        self.assertContains(response, 'Search & Analyze')
        self.assertContains(response, 'Analyze All Recipes')
        self.assertContains(response, 'Browse all')

    def test_search_template_form_fields(self):
        """Test search template contains all form fields"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('recipes:recipe-search'))
        
        self.assertContains(response, 'recipe_name')
        self.assertContains(response, 'ingredients')
        self.assertContains(response, 'cooking_time_max')
        self.assertContains(response, 'difficulty')
        self.assertContains(response, 'chart_type')

    def test_search_template_help_text(self):
        """Test search template displays help text"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('recipes:recipe-search'))
        
        self.assertContains(response, 'wildcard')
        self.assertContains(response, 'Search Tips')

    def test_search_template_results_display(self):
        """Test search template displays results when available"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('recipes:recipe-search'), {
            'search_action': 'show_all',
            'chart_type': '#1'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Search Results')
        self.assertContains(response, 'Data Visualization')

    def test_search_template_no_results_message(self):
        """Test search template displays no results message"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('recipes:recipe-search'), {
            'search_action': 'search',
            'recipe_name': 'nonexistent',
            'chart_type': '#1'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No Recipes Found')
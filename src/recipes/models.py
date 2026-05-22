from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFit


class PublishedRecipeManager(models.Manager):
    """Returns only recipes whose status is 'published'."""

    def get_queryset(self):
        return super().get_queryset().filter(status=Recipe.Status.PUBLISHED)


class Recipe(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    name = models.CharField(max_length=120, help_text="Enter the recipe name")
    short_description = models.TextField(
        max_length=300, blank=True, help_text="Enter a short description of the recipe"
    )
    ingredients = models.TextField(help_text="Enter ingredients (comma separated)")
    cooking_time = models.IntegerField(
        help_text="Enter cooking time (in minutes)",
        validators=[
            MinValueValidator(1, message="Cooking time must be at least 1 minute"),
            MaxValueValidator(1440, message="Cooking time cannot exceed 24 hours (1440 minutes)"),
        ],
    )
    difficulty = models.CharField(
        max_length=20, blank=True, editable=False, help_text="Difficulty level (auto-calculated, readonly)"
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
        help_text="Only published recipes are visible to non-staff users.",
    )
    likes = models.IntegerField(default=0, editable=False, help_text="Number of likes (auto-calculated, readonly)")
    comments = models.TextField(blank=True, editable=False, help_text="User comments (future feature, readonly)")
    references = models.URLField(blank=True, help_text="Optional reference URL")
    recipe_image = models.ImageField(
        upload_to="recipes",
        default="recipes/no_picture.png",
        help_text="Upload image or use filename from static/images/recipes/ (e.g., 'recipes/image.jpg')",
    )
    image_small = ImageSpecField(
        source="recipe_image",
        processors=[ResizeToFit(400, 400)],
        format="WEBP",
        options={"quality": 72},
    )
    image_medium = ImageSpecField(
        source="recipe_image",
        processors=[ResizeToFit(800, 800)],
        format="WEBP",
        options={"quality": 72},
    )
    image_large = ImageSpecField(
        source="recipe_image",
        processors=[ResizeToFit(1200, 1200)],
        format="WEBP",
        options={"quality": 72},
    )

    objects = models.Manager()
    published = PublishedRecipeManager()

    @classmethod
    def visible_to(cls, user):
        """Queryset filtered to what `user` is allowed to see.

        Staff users get the unfiltered queryset (drafts + published).
        Everyone else (regular logged-in users, anonymous) gets published only.
        Centralizing this rule here means views don't repeat the filter logic.
        """
        if getattr(user, "is_staff", False):
            return cls.objects.all()
        return cls.published.all()

    def clean(self):
        """Custom validation method"""
        super().clean()

        # Validate that ingredients is not empty or just whitespace
        if not self.ingredients or not self.ingredients.strip():
            raise ValidationError({"ingredients": "Ingredients cannot be empty."})

        # Validate that name is not empty or just whitespace
        if not self.name or not self.name.strip():
            raise ValidationError({"name": "Recipe name cannot be empty."})

        # Validate that cooking time is reasonable
        if self.cooking_time <= 0:
            raise ValidationError({"cooking_time": "Cooking time must be greater than 0."})

    def return_ingredients_as_list(self):
        # Convert ingredients string to list
        if not self.ingredients or self.ingredients.strip() == "":
            return []
        else:
            return [ingredient.strip() for ingredient in self.ingredients.split(",") if ingredient.strip()]

    def calculate_difficulty(self):
        # Calculate difficulty based on cooking time and number of ingredients
        # Use the helper method to get ingredients as a list
        ingredients_list = self.return_ingredients_as_list()
        num_ingredients = len(ingredients_list)

        if self.cooking_time < 10 and num_ingredients < 4:
            return "Easy"
        elif self.cooking_time < 10 and num_ingredients >= 4:
            return "Medium"
        elif self.cooking_time >= 10 and num_ingredients < 4:
            return "Intermediate"
        elif self.cooking_time >= 10 and num_ingredients >= 4:
            return "Hard"

    def save(self, *args, **kwargs):
        # Auto-calculate difficulty before saving
        self.difficulty = self.calculate_difficulty()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]

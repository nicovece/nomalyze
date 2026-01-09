from django import forms

# Difficulty choices based on your Recipe model
DIFFICULTY_CHOICES = (
    ("", "All Difficulties"),
    ("Easy", "Easy"),
    ("Medium", "Medium"),
    ("Intermediate", "Intermediate"),
    ("Hard", "Hard"),
)


class RecipeSearchForm(forms.Form):
    # Search criteria fields
    recipe_name = forms.CharField(
        max_length=120,
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter recipe name (supports * and ? wildcards)",
                # 'class': INPUT_CLASSES
            }
        ),
        help_text="Use * for any characters, ? for single character. Example: 'pasta*' or 'pasta?'",
    )

    ingredients = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter ingredients (comma separated, supports wildcards)",
                # 'class': INPUT_CLASSES
            }
        ),
        help_text="Use * for any characters, ? for single character. Example: 'tomato*, cheese'",
    )

    cooking_time_max = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=1440,
        widget=forms.NumberInput(
            attrs={
                "placeholder": "Max cooking time (minutes)",
                # 'class': INPUT_CLASSES
            }
        ),
    )

    difficulty = forms.ChoiceField(choices=DIFFICULTY_CHOICES, required=False)

from django.db import migrations


def backfill_to_published(apps, schema_editor):
    """Pre-existing recipes were public before this feature shipped.

    Set every existing row to 'published' so the public site doesn't go
    empty when views start filtering on status. New recipes created
    after this migration runs will follow the model default of 'draft'.
    """
    Recipe = apps.get_model("recipes", "Recipe")
    Recipe.objects.update(status="published")


def reverse_to_draft(apps, schema_editor):
    """Reverse: revert every recipe to draft so the schema can be rolled back."""
    Recipe = apps.get_model("recipes", "Recipe")
    Recipe.objects.update(status="draft")


class Migration(migrations.Migration):
    dependencies = [
        ("recipes", "0009_recipe_status"),
    ]

    operations = [
        migrations.RunPython(backfill_to_published, reverse_to_draft),
    ]

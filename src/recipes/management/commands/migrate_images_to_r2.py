"""
One-shot: upload existing recipe images from the repo's static/images/recipes/
directory into the configured default storage (R2 in production), preserving
each Recipe row's image filename.

Run with USE_R2_STORAGE=True so Recipe.recipe_image.save() writes to R2.
Idempotent: skips recipes whose image is already present in the storage backend
unless --force is passed.
"""

import os

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand

from recipes.models import Recipe


class Command(BaseCommand):
    help = "Upload existing recipe images from static/images/recipes/ into the default storage backend."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be uploaded without writing.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-upload even if the storage backend already reports the file exists.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        force = options["force"]

        static_dir = os.path.join(settings.BASE_DIR, "static", "images", "recipes")
        if not os.path.isdir(static_dir):
            self.stderr.write(self.style.ERROR(f"Static dir not found: {static_dir}"))
            return

        uploaded = skipped = missing = 0

        for recipe in Recipe.objects.all().order_by("id"):
            current_path = str(recipe.recipe_image) if recipe.recipe_image else ""
            filename = os.path.basename(current_path) if current_path else ""

            if not filename:
                self.stdout.write(f"[skip ] recipe {recipe.id} ({recipe.name}): no image set")
                skipped += 1
                continue

            local_path = os.path.join(static_dir, filename)
            if not os.path.exists(local_path):
                self.stdout.write(
                    self.style.WARNING(
                        f"[miss ] recipe {recipe.id} ({recipe.name}): {filename} not in static/images/recipes/"
                    )
                )
                missing += 1
                continue

            target_key = f"recipes/{filename}"
            already_there = recipe.recipe_image.storage.exists(target_key)

            if already_there and not force:
                self.stdout.write(f"[have ] recipe {recipe.id}: {target_key} already in storage")
                skipped += 1
                continue

            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(f"[plan ] recipe {recipe.id}: would upload {local_path} -> {target_key}")
                )
                uploaded += 1
                continue

            with open(local_path, "rb") as fh:
                # save() on the FieldFile writes through the storage backend AND
                # triggers imagekit's Optimistic strategy to generate variants.
                recipe.recipe_image.save(filename, File(fh), save=True)
                # Force eager URL access in case the strategy did not run.
                _ = recipe.image_small.url
                _ = recipe.image_medium.url
                _ = recipe.image_large.url

            self.stdout.write(self.style.SUCCESS(f"[done ] recipe {recipe.id}: uploaded {target_key} + variants"))
            uploaded += 1

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Summary - uploaded: {uploaded}, skipped: {skipped}, missing: {missing}"))

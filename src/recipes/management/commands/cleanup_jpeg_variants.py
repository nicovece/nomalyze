"""
One-shot: delete orphaned `.jpg`/`.jpeg` variants under CACHE/images/recipes/
in object storage. After the WebP cutover (`.prd/webp-images-plan.md`),
imagekit generates `.webp` variants and the previous JPEG variants are no
longer referenced anywhere — this command reclaims that storage.

Run only against R2 (USE_R2_STORAGE=True). Idempotent: subsequent runs find
nothing to delete.
"""

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Delete orphaned .jpg/.jpeg variants from CACHE/images/recipes/ in object storage."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List targets without deleting.",
        )

    def handle(self, *args, **options):
        if not getattr(settings, "USE_R2_STORAGE", False):
            raise CommandError(
                "Refusing to run: USE_R2_STORAGE is not True. "
                "This command targets the S3-compatible bucket, not local files."
            )

        dry_run = options["dry_run"]
        prefix = "CACHE/images/recipes/"
        deleted = kept = 0

        for obj in default_storage.bucket.objects.filter(Prefix=prefix):
            key = obj.key
            lower = key.lower()
            if lower.endswith(".jpg") or lower.endswith(".jpeg"):
                if dry_run:
                    self.stdout.write(f"[plan ] delete {key}")
                else:
                    obj.delete()
                    self.stdout.write(self.style.SUCCESS(f"[done ] deleted {key}"))
                deleted += 1
            else:
                kept += 1

        self.stdout.write("")
        action = "would delete" if dry_run else "deleted"
        self.stdout.write(self.style.SUCCESS(f"Summary - {action}: {deleted}, kept (non-jpeg): {kept}"))

from django.core.management.base import BaseCommand
from docvault.models import Document, DocumentVersion
from django.db import transaction

class Command(BaseCommand):
    help = 'Fix v1 DocumentVersion created_at to match Document created_at.'

    def handle(self, *args, **options):
        updated = 0
        with transaction.atomic():
            for doc in Document.objects.all():
                v1 = doc.versions.order_by('version_number').first()
                if v1 and v1.version_number == 1 and v1.created_at != doc.created_at:
                    self.stdout.write(f"Fixing v1 for Document '{doc.title}' (ID {doc.id}): {v1.created_at} -> {doc.created_at}")
                    v1.created_at = doc.created_at
                    v1.save(update_fields=['created_at'])
                    updated += 1
        self.stdout.write(self.style.SUCCESS(f"Updated {updated} v1 DocumentVersion dates.")) 
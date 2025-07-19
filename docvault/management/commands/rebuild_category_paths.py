from django.core.management.base import BaseCommand
from django.db import transaction
from docvault.models import DocumentCategory


class Command(BaseCommand):
    help = 'Rebuild materialized paths for all categories'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Get all categories and sort by depth to ensure parents are processed first
        categories = DocumentCategory.objects.all().order_by('depth', 'id')
        
        if not categories.exists():
            self.stdout.write(self.style.SUCCESS('No categories found'))
            return
        
        self.stdout.write(f'Found {categories.count()} categories')
        
        with transaction.atomic():
            for category in categories:
                old_path = category.path
                old_depth = category.depth
                
                # Calculate new values
                if category.parent:
                    new_depth = category.parent.depth + 1
                    new_path = f"{category.parent.path}.{category.id}"
                else:
                    new_depth = 0
                    new_path = str(category.id)
                
                if old_path != new_path or old_depth != new_depth:
                    if dry_run:
                        self.stdout.write(
                            f'Would update {category.name}: '
                            f'path "{old_path}" -> "{new_path}", '
                            f'depth {old_depth} -> {new_depth}'
                        )
                    else:
                        category.path = new_path
                        category.depth = new_depth
                        category.save(update_fields=['path', 'depth'])
                        self.stdout.write(
                            f'Updated {category.name}: '
                            f'path "{old_path}" -> "{new_path}", '
                            f'depth {old_depth} -> {new_depth}'
                        )
                else:
                    self.stdout.write(f'✓ {category.name} is correct')
        
        if not dry_run:
            self.stdout.write(self.style.SUCCESS('Successfully rebuilt all category paths'))
        else:
            self.stdout.write(self.style.SUCCESS('Dry run completed')) 
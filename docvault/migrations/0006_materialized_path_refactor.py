# Generated manually for materialized path refactor

from django.db import migrations, models
import django.db.models.deletion


def populate_materialized_paths(apps, schema_editor):
    """Populate the new path and depth fields from existing hierarchy"""
    DocumentCategory = apps.get_model('docvault', 'DocumentCategory')
    
    def set_path_and_depth(category, parent_path=""):
        """Recursively set path and depth for a category and its children"""
        # Set depth
        category.depth = len(parent_path.split('.')) if parent_path else 0
        
        # Save to get ID if it's a new category
        category.save()
        
        # Set path
        if parent_path:
            category.path = f"{parent_path}.{category.id}"
        else:
            category.path = str(category.id)
        
        category.save(update_fields=['path', 'depth'])
        
        # Process children
        for child in category.children.all():
            set_path_and_depth(child, category.path)
    
    # Start with root categories
    root_categories = DocumentCategory.objects.filter(parent=None)
    for root in root_categories:
        set_path_and_depth(root)


def reverse_populate_materialized_paths(apps, schema_editor):
    """Reverse migration - clear path and depth fields"""
    DocumentCategory = apps.get_model('docvault', 'DocumentCategory')
    DocumentCategory.objects.all().update(path='', depth=0)


class Migration(migrations.Migration):

    dependencies = [
        ('docvault', '0005_changelog_importance_changelog_show_in_global'),
    ]

    operations = [
        # Add parent field first
        migrations.AddField(
            model_name='documentcategory',
            name='parent',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='children',
                to='docvault.documentcategory'
            ),
        ),
        
        # Add new fields
        migrations.AddField(
            model_name='documentcategory',
            name='path',
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text='Materialized path for hierarchy (e.g., "1.5.12")',
                max_length=255
            ),
        ),
        migrations.AddField(
            model_name='documentcategory',
            name='depth',
            field=models.PositiveIntegerField(
                default=0,
                db_index=True,
                help_text='Depth in the tree (0 for root)'
            ),
        ),
        
        # Add indexes
        migrations.AddIndex(
            model_name='documentcategory',
            index=models.Index(fields=['path'], name='docvault_doc_path_idx'),
        ),
        migrations.AddIndex(
            model_name='documentcategory',
            index=models.Index(fields=['depth'], name='docvault_doc_depth_idx'),
        ),
        migrations.AddIndex(
            model_name='documentcategory',
            index=models.Index(fields=['path', 'depth'], name='docvault_doc_path_depth_idx'),
        ),
        
        # Change slug from unique to unique_together with parent
        migrations.AlterUniqueTogether(
            name='documentcategory',
            unique_together={('parent', 'slug')},
        ),
        
        # Set ordering
        migrations.AlterModelOptions(
            name='documentcategory',
            options={'ordering': ['path'], 'verbose_name_plural': 'Document Categories'},
        ),
        
        # Populate the new fields
        migrations.RunPython(
            populate_materialized_paths,
            reverse_populate_materialized_paths,
        ),
    ] 
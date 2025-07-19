from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.text import slugify
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache

# Conditionally import TinyMCE based on settings
if getattr(settings, 'DOCVAULT_EDITOR', 'text') == 'tinymce':
    from tinymce.models import HTMLField
    ContentField = HTMLField
else:
    ContentField = models.TextField

class DocumentCategory(models.Model):
    """Categories for documents with materialized path for optimal performance"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, help_text='URL-friendly identifier for the category')
    description = models.TextField(blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    
    # Materialized path for efficient tree operations
    path = models.CharField(max_length=255, db_index=True, blank=True, help_text='Materialized path for hierarchy (e.g., "1.5.12")')
    depth = models.PositiveIntegerField(default=0, db_index=True, help_text='Depth in the tree (0 for root)')
    
    class Meta:
        verbose_name_plural = "Document Categories"
        unique_together = [['parent', 'slug']]  # Slug must be unique within parent
        indexes = [
            models.Index(fields=['path']),
            models.Index(fields=['depth']),
            models.Index(fields=['path', 'depth']),
        ]
        ordering = ['path']

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    def get_ancestors(self, include_self=False):
        """Get all ancestors in a single query"""
        if not self.path:
            # Fallback: collect parent IDs first, then single query
            parent_ids = []
            current = self if include_self else self.parent
            
            while current:
                parent_ids.insert(0, current.id)  # Insert at beginning to maintain order
                current = current.parent
            
            if not parent_ids:
                return []
            
            # Single query to get all ancestors
            return self.__class__.objects.filter(id__in=parent_ids).order_by('depth')
        
        path_parts = self.path.split('.')
        if not include_self:
            path_parts = path_parts[:-1]  # Exclude self
        
        if not path_parts:
            return []
        
        return self.__class__.objects.filter(
            id__in=path_parts
        ).order_by('depth')

    def get_descendants(self, include_self=False):
        """Get all descendants in a single query"""
        if not self.path:
            return self.__class__.objects.none()
        
        queryset = self.__class__.objects.filter(path__startswith=self.path)
        if not include_self:
            queryset = queryset.exclude(pk=self.pk)
        
        return queryset.order_by('path')

    def get_siblings(self, include_self=False):
        """Get all siblings (same parent)"""
        if not self.parent:
            return self.__class__.objects.filter(parent=None)
        
        queryset = self.__class__.objects.filter(parent=self.parent)
        if not include_self:
            queryset = queryset.exclude(pk=self.pk)
        
        return queryset

    def get_url_path(self):
        """Generate URL path from ancestors"""
        ancestors = self.get_ancestors(include_self=True)
        if not ancestors:
            # Fallback: just return the category slug
            return self.slug
        
        return '/'.join([cat.slug for cat in ancestors])

    def get_absolute_url(self):
        """Returns the URL for this category"""
        return reverse('docvault:document_list_by_category', kwargs={'category_path': self.get_url_path()})

    def get_all_documents(self):
        """Returns all documents in this category and its descendants"""
        descendant_ids = self.get_descendants(include_self=True).values_list('id', flat=True)
        return Document.objects.filter(category_id__in=descendant_ids)

    @classmethod
    def get_by_path(cls, category_path):
        """Get category by URL path with optimized query"""
        if not category_path:
            return None
        
        slugs = category_path.split('/')
        if not slugs:
            return None
        
        # If it's a single slug, just find it directly
        if len(slugs) == 1:
            try:
                return cls.objects.get(slug=slugs[0])
            except cls.DoesNotExist:
                return None
        
        # For nested paths, find by the last slug and verify the full path
        last_slug = slugs[-1]
        try:
            category = cls.objects.get(slug=last_slug)
            
            # Build the expected path by traversing up the hierarchy
            expected_path = []
            current = category
            while current:
                expected_path.insert(0, current.slug)
                current = current.parent
            
            expected_path_str = '/'.join(expected_path)
            
            if expected_path_str == category_path:
                return category
            else:
                return None
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_breadcrumbs(cls, category):
        """Get breadcrumb trail with single query"""
        if not category:
            return []
        
        return category.get_ancestors(include_self=True)

    @property
    def is_parent(self):
        """Returns True if this category has children"""
        return self.children.exists()

    @property
    def is_child(self):
        """Returns True if this category has a parent"""
        return self.parent is not None

    @property
    def is_root(self):
        """Returns True if this is a root category"""
        return self.parent is None

    def save(self, *args, **kwargs):
        # Set depth based on parent
        if self.parent:
            self.depth = self.parent.depth + 1
        else:
            self.depth = 0
        
        # Save first to get the ID
        super().save(*args, **kwargs)
        
        # Update path based on parent
        if self.parent:
            self.path = f"{self.parent.path}.{self.id}"
        else:
            self.path = str(self.id)
        
        # Save again with updated path
        super().save(update_fields=['path'])
        
        # Update all descendants' paths
        self._update_descendant_paths()

    def _update_descendant_paths(self):
        """Update paths for all descendants when this category's path changes"""
        descendants = self.children.all()
        for descendant in descendants:
            descendant.path = f"{self.path}.{descendant.id}"
            descendant.depth = self.depth + 1
            descendant.save(update_fields=['path', 'depth'])
            descendant._update_descendant_paths()

    def move_to(self, new_parent):
        """Move this category to a new parent"""
        if new_parent == self.parent:
            return  # No change needed
        
        # Prevent circular references
        if new_parent and new_parent in self.get_descendants():
            raise ValueError("Cannot move category to its own descendant")
        
        self.parent = new_parent
        self.save()

class Document(models.Model):
    """Main document model with content and version tracking"""
    title = models.CharField(max_length=200, help_text='The title of the document')
    slug = models.SlugField(max_length=200, help_text='URL-friendly version of the title')
    content = ContentField(help_text='The main content of the document')
    category = models.ForeignKey(DocumentCategory, on_delete=models.PROTECT, related_name='documents')
    created_at = models.DateTimeField(default=timezone.now, help_text='Date/time the document was created')
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_documents')

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        """Returns the URL to access a particular document"""
        return reverse('docvault:document_detail', kwargs={
            'category_path': self.category.get_url_path(),
            'document_slug': self.slug
        })

    def generate_toc(self):
        """
        Generate a table of contents from HTML headings in the content.
        Returns a list of tuples: (heading_level, heading_text, heading_id)
        """
        import re
        headings = []

        # Find all heading tags (h1-h6) with their content
        heading_pattern = re.compile(r'<h([1-6])(?:[^>]*)>(.*?)</h\1>', re.IGNORECASE | re.DOTALL)
        matches = heading_pattern.finditer(self.content)

        for match in matches:
            level = int(match.group(1))
            text = match.group(2)

            # Strip any HTML tags from the heading text
            clean_text = re.sub(r'<.*?>', '', text)

            # Generate an ID based on the text (for anchor links)
            heading_id = clean_text.lower().strip()
            heading_id = re.sub(r'[^\w\s-]', '', heading_id)  # Remove special chars
            heading_id = re.sub(r'\s+', '-', heading_id)      # Replace spaces with hyphens

            headings.append((level, clean_text, heading_id))

        return headings

    def save(self, *args, **kwargs):
        # Only set created_at if this is a new object and not already set
        if not self.pk and not self.created_at:
            self.created_at = timezone.now()

        # Check if this is an update to an existing document
        if self.pk:
            # Get the original document before changes
            original = Document.objects.get(pk=self.pk)

            # If content changed, create a new version
            if original.content != self.content:
                super().save(*args, **kwargs)

                # Create a new version
                version = DocumentVersion.objects.create(
                    document=self,
                    content=self.content,
                    created_by=self.created_by
                )

                return

        # If it's a new document or no content changed
        super().save(*args, **kwargs)

class DocumentVersion(models.Model):
    """Stores each version of a document's content"""
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='versions')
    content = ContentField(help_text='The content for this version')
    version_number = models.PositiveIntegerField(help_text='Automatically incremented version number')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version_number']
        unique_together = ('document', 'version_number')

    def __str__(self):
        return f"{self.document.title} - v{self.version_number}"

    def save(self, *args, **kwargs):
        # Auto-increment version number
        if not self.version_number:
            latest = DocumentVersion.objects.filter(document=self.document).order_by('-version_number').first()
            self.version_number = 1 if latest is None else latest.version_number + 1

        super().save(*args, **kwargs)

class Changelog(models.Model):
    """Records changes made to documents with descriptions"""
    IMPORTANCE_CHOICES = [
        ('MINOR', 'Minor - Small wording or formatting changes'),
        ('NORMAL', 'Normal - Notable changes to content'),
        ('MAJOR', 'Major - Critical changes that users should be aware of')
    ]
    
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='changelogs')
    description = models.TextField(help_text='Description of changes made')
    importance = models.CharField(
        max_length=6, 
        choices=IMPORTANCE_CHOICES, 
        default='NORMAL',
        help_text='Determines visibility in the global changelog'
    )
    show_in_global = models.BooleanField(
        default=False,
        help_text='Explicitly include this change in the global changelog regardless of importance'
    )
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    version = models.ForeignKey(DocumentVersion, on_delete=models.SET_NULL, null=True, blank=True, related_name='changelog')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Change to {self.document.title} on {self.created_at.strftime('%Y-%m-%d')}"

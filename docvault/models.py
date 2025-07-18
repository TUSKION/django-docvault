from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.text import slugify
from django.utils import timezone
from django.conf import settings

# Conditionally import TinyMCE based on settings
if getattr(settings, 'DOCVAULT_EDITOR', 'text') == 'tinymce':
    from tinymce.models import HTMLField
    ContentField = HTMLField
else:
    ContentField = models.TextField

class DocumentCategory(models.Model):
    """Categories for documents (e.g., Legal, Financial, Personal)"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, help_text='URL-friendly identifier for the category')
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Document Categories"

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
        return reverse('docvault:document_detail', args=[str(self.category.slug), str(self.slug)])

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

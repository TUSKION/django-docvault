from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View
from django.http import Http404
from django.db.models import Q

from .models import Document, DocumentCategory, DocumentVersion, Changelog


class DocumentListView(ListView):
    model = Document
    template_name = 'docvault/document_list.html'
    context_object_name = 'documents'
    paginate_by = 10

    def get_queryset(self):
        return Document.objects.all().select_related('category', 'created_by').order_by('-updated_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = DocumentCategory.objects.filter(parent=None).prefetch_related('children', 'documents')
        return context


class CategoryListView(ListView):
    model = DocumentCategory
    template_name = 'docvault/category_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        return DocumentCategory.objects.filter(parent=None).prefetch_related('children', 'documents')


class DocumentListByCategoryView(ListView):
    model = Document
    template_name = 'docvault/document_list.html'
    context_object_name = 'documents'
    paginate_by = 10

    def get_queryset(self):
        # Single query using indexed full_path field
        self.category = DocumentCategory.get_by_path(self.kwargs['category_path'])
        if not self.category:
            raise Http404("Category not found")
        
        return Document.objects.filter(category=self.category).select_related('category', 'created_by').order_by('-updated_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        context['categories'] = DocumentCategory.objects.filter(parent=None).prefetch_related('children', 'documents')
        
        # Optimized breadcrumb generation
        context['breadcrumbs'] = DocumentCategory.get_breadcrumbs(self.category)
        
        return context


class DocumentDetailView(DetailView):
    model = Document
    template_name = 'docvault/document_detail.html'
    context_object_name = 'document'

    def get_object(self):
        # Single query for category lookup
        category = DocumentCategory.get_by_path(self.kwargs['category_path'])
        if not category:
            raise Http404("Category not found")
        
        return get_object_or_404(
            Document,
            category=category,
            slug=self.kwargs['document_slug']
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        document = self.get_object()

        # Get the most recent versions and changelogs
        context['recent_versions'] = document.versions.all()[:5]
        context['recent_changes'] = document.changelogs.all()[:5]

        # Generate table of contents
        context['table_of_contents'] = document.generate_toc()

        # Optimized breadcrumb generation
        context['breadcrumbs'] = DocumentCategory.get_breadcrumbs(document.category)

        return context


class VersionHistoryView(ListView):
    template_name = 'docvault/version_history.html'
    context_object_name = 'versions'
    paginate_by = 15

    def get_document(self):
        # Single query for category lookup
        category = DocumentCategory.get_by_path(self.kwargs['category_path'])
        if not category:
            raise Http404("Category not found")
        
        return get_object_or_404(
            Document,
            category=category,
            slug=self.kwargs['document_slug']
        )

    def get_queryset(self):
        self.document = self.get_document()
        return DocumentVersion.objects.filter(document=self.document).order_by('-version_number')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['document'] = self.document
        
        # Optimized breadcrumb generation
        context['breadcrumbs'] = DocumentCategory.get_breadcrumbs(self.document.category)
        
        return context


class DocumentVersionView(DetailView):
    template_name = 'docvault/document_version.html'
    context_object_name = 'version'

    def get_document(self):
        # Single query for category lookup
        category = DocumentCategory.get_by_path(self.kwargs['category_path'])
        if not category:
            raise Http404("Category not found")
        
        return get_object_or_404(
            Document,
            category=category,
            slug=self.kwargs['document_slug']
        )

    def get_object(self):
        self.document = self.get_document()
        return get_object_or_404(
            DocumentVersion,
            document=self.document,
            version_number=self.kwargs['version_number']
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['document'] = self.document

        # Generate TOC for this specific version's content using Document's method
        # avoids creating a method to generate the toc in the version etc
        original_content = self.document.content
        self.document.content = self.object.content
        context['table_of_contents'] = self.document.generate_toc()
        self.document.content = original_content  # Restore original content

        # Get previous and next versions if they exist
        current_version = self.object.version_number
        context['previous_version'] = DocumentVersion.objects.filter(
            document=self.document,
            version_number__lt=current_version
        ).order_by('-version_number').first()

        context['next_version'] = DocumentVersion.objects.filter(
            document=self.document,
            version_number__gt=current_version
        ).order_by('version_number').first()

        # Get changelog for this version if exists
        try:
            context['changelog'] = Changelog.objects.get(version=self.object)
        except Changelog.DoesNotExist:
            context['changelog'] = None

        # Optimized breadcrumb generation
        context['breadcrumbs'] = DocumentCategory.get_breadcrumbs(self.document.category)

        return context


class DocumentChangelogView(ListView):
    template_name = 'docvault/document_changelog.html'
    context_object_name = 'changelogs'
    paginate_by = 15

    def get_document(self):
        # Single query for category lookup
        category = DocumentCategory.get_by_path(self.kwargs['category_path'])
        if not category:
            raise Http404("Category not found")
        
        return get_object_or_404(
            Document,
            category=category,
            slug=self.kwargs['document_slug']
        )

    def get_queryset(self):
        self.document = self.get_document()
        return Changelog.objects.filter(document=self.document).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['document'] = self.document
        
        # Optimized breadcrumb generation
        context['breadcrumbs'] = DocumentCategory.get_breadcrumbs(self.document.category)
        
        return context


class DocumentSearchView(ListView):
    """Search for documents by title and content"""
    model = Document
    template_name = 'docvault/search_results.html'
    context_object_name = 'documents'
    paginate_by = 10

    def get_queryset(self):
        query = self.request.GET.get('q', '')
        if query:
            return Document.objects.filter(
                Q(title__icontains=query) |
                Q(content__icontains=query)
            ).select_related('category', 'created_by').order_by('-updated_at')
        return Document.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['categories'] = DocumentCategory.objects.filter(parent=None).prefetch_related('children', 'documents')
        return context


class GlobalChangelogView(ListView):
    """Shows important changes across all documents"""
    template_name = 'docvault/global_changelog.html'
    context_object_name = 'changelogs'
    paginate_by = 20

    def get_queryset(self):
        # Get MAJOR changes and any explicitly marked for global inclusion
        return Changelog.objects.filter(
            Q(importance='MAJOR') | Q(show_in_global=True)
        ).select_related('document', 'document__category', 'created_by').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = DocumentCategory.objects.filter(parent=None).prefetch_related('children', 'documents')
        return context


class DocumentCompareView(View):
    """Compare two versions of a document and show the differences"""
    template_name = 'docvault/document_compare.html'

    def get(self, request, category_path, document_slug):
        # Single query for category lookup
        category = DocumentCategory.get_by_path(category_path)
        if not category:
            raise Http404("Category not found")
        
        document = get_object_or_404(Document, category=category, slug=document_slug)
        
        # Get the two versions to compare
        version1_id = request.GET.get('v1')
        version2_id = request.GET.get('v2')
        
        if not version1_id or not version2_id:
            # Default to comparing current version with previous version
            versions = document.versions.all()[:2]
            if len(versions) >= 2:
                version1 = versions[1]  # Previous version
                version2 = versions[0]  # Current version
            else:
                version1 = version2 = versions[0] if versions else None
        else:
            version1 = get_object_or_404(DocumentVersion, document=document, version_number=version1_id)
            version2 = get_object_or_404(DocumentVersion, document=document, version_number=version2_id)
        
        # Optimized breadcrumb generation
        breadcrumbs = DocumentCategory.get_breadcrumbs(document.category)
        
        context = {
            'document': document,
            'version1': version1,
            'version2': version2,
            'breadcrumbs': breadcrumbs,
            'categories': DocumentCategory.objects.filter(parent=None).prefetch_related('children', 'documents')
        }
        
        return render(request, self.template_name, context)

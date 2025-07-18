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
        context['categories'] = DocumentCategory.objects.all().prefetch_related('documents')
        return context


class CategoryListView(ListView):
    model = DocumentCategory
    template_name = 'docvault/category_list.html'
    context_object_name = 'categories'


class DocumentListByCategoryView(ListView):
    model = Document
    template_name = 'docvault/document_list.html'
    context_object_name = 'documents'
    paginate_by = 10

    def get_queryset(self):
        self.category = get_object_or_404(DocumentCategory, slug=self.kwargs['category_slug'])
        return Document.objects.filter(category=self.category).select_related('category', 'created_by').order_by('-updated_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        context['categories'] = DocumentCategory.objects.all().prefetch_related('documents')
        return context


class DocumentDetailView(DetailView):
    model = Document
    template_name = 'docvault/document_detail.html'
    context_object_name = 'document'

    def get_object(self):
        return get_object_or_404(
            Document,
            category__slug=self.kwargs['category_slug'],
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

        return context


class VersionHistoryView(ListView):
    template_name = 'docvault/version_history.html'
    context_object_name = 'versions'
    paginate_by = 15

    def get_document(self):
        return get_object_or_404(
            Document,
            category__slug=self.kwargs['category_slug'],
            slug=self.kwargs['document_slug']
        )

    def get_queryset(self):
        self.document = self.get_document()
        return DocumentVersion.objects.filter(document=self.document).order_by('-version_number')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['document'] = self.document
        return context


class DocumentVersionView(DetailView):
    template_name = 'docvault/document_version.html'
    context_object_name = 'version'

    def get_document(self):
        return get_object_or_404(
            Document,
            category__slug=self.kwargs['category_slug'],
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

        return context


class DocumentChangelogView(ListView):
    template_name = 'docvault/document_changelog.html'
    context_object_name = 'changelogs'
    paginate_by = 15

    def get_document(self):
        return get_object_or_404(
            Document,
            category__slug=self.kwargs['category_slug'],
            slug=self.kwargs['document_slug']
        )

    def get_queryset(self):
        self.document = self.get_document()
        return Changelog.objects.filter(document=self.document).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['document'] = self.document
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
        context['categories'] = DocumentCategory.objects.all().prefetch_related('documents')
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
        ).select_related('document', 'document__category', 'version', 'created_by').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = DocumentCategory.objects.all()
        return context


class DocumentCompareView(View):
    """Compare two versions of a document and show the differences"""
    template_name = 'docvault/document_compare.html'

    def get(self, request, category_slug, document_slug):
        # Get the document
        document = get_object_or_404(
            Document,
            category__slug=category_slug,
            slug=document_slug
        )

        # Get version numbers from query parameters
        version1_num = request.GET.get('v1')
        version2_num = request.GET.get('v2')

        # If versions aren't specified, show version selection form
        if not version1_num or not version2_num:
            versions = document.versions.all().order_by('-version_number')
            return render(request, self.template_name, {
                'document': document,
                'versions': versions,
                'compare_mode': 'select'
            })

        # Get the specified versions
        try:
            version1 = DocumentVersion.objects.get(
                document=document,
                version_number=int(version1_num)
            )
            version2 = DocumentVersion.objects.get(
                document=document,
                version_number=int(version2_num)
            )
        except (DocumentVersion.DoesNotExist, ValueError):
            # Handle invalid version numbers
            return redirect(document.get_absolute_url())

        return render(request, self.template_name, {
            'document': document,
            'version1': version1,
            'version2': version2,
            'compare_mode': 'diff'
        })

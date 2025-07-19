from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View
from django.http import Http404
from django.db.models import Q, Count

from .models import Document, DocumentCategory, DocumentVersion, Changelog
from .mixins import CategoryContextMixin, DocumentContextMixin
from .utils import get_optimized_categories_queryset, compute_url_paths, get_documents_for_category


class DocumentListView(CategoryContextMixin, ListView):
    model = Document
    template_name = 'docvault/document_list.html'
    context_object_name = 'documents'
    paginate_by = 10

    def get_queryset(self):
        return Document.objects.all().select_related('category', 'created_by').order_by('-updated_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = self.get_categories_with_url_paths()
        return context


class CategoryListView(CategoryContextMixin, ListView):
    model = DocumentCategory
    template_name = 'docvault/category_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        return get_optimized_categories_queryset()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Use pre-fetched data if available (from SmartRouterView)
        if hasattr(self.request, '_prefetched_data'):
            # Use the pre-fetched categories that already have cached_url_path computed
            context['categories'] = [cat for cat in self.request._prefetched_data['all_categories'] if cat.parent is None]
        else:
            # Pre-compute URL paths for categories (required by base template)
            compute_url_paths(context['categories'])
        
        return context


class DocumentListByCategoryView(CategoryContextMixin, ListView):
    model = Document
    template_name = 'docvault/document_list.html'
    context_object_name = 'documents'
    paginate_by = 10

    def get_queryset(self):
        # Use pre-fetched data if available (from SmartRouterView)
        if hasattr(self.request, '_prefetched_data') and hasattr(self.request, '_category_cache'):
            category = self.request._category_cache.get(self.kwargs['category_path'])
            if category:
                self.category = category
                return get_documents_for_category(
                    category, 
                    use_prefetched_data=True, 
                    prefetched_documents=self.request._prefetched_data['all_documents']
                )
        
        # Fallback: Get category with all optimizations in one query
        optimized_qs = DocumentCategory.objects.select_related('parent')\
            .prefetch_related('children', 'children__documents', 'documents')\
            .annotate(document_count=Count('documents'), child_count=Count('children'))
        
        self.category = DocumentCategory.get_by_path(self.kwargs['category_path'], queryset=optimized_qs)
        
        if not self.category:
            raise Http404("Category not found")
        
        return get_documents_for_category(self.category)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        context['categories'] = self.get_categories_with_url_paths()
        
        # Optimized breadcrumb generation (cached)
        if not hasattr(self.request, '_breadcrumbs_cache'):
            self.request._breadcrumbs_cache = {}
        
        breadcrumb_key = f"breadcrumbs_{self.category.id}"
        if breadcrumb_key not in self.request._breadcrumbs_cache:
            self.request._breadcrumbs_cache[breadcrumb_key] = DocumentCategory.get_breadcrumbs(self.category)
        
        context['breadcrumbs'] = self.request._breadcrumbs_cache[breadcrumb_key]
        
        return context


class DocumentDetailView(CategoryContextMixin, DocumentContextMixin, DetailView):
    model = Document
    template_name = 'docvault/document_detail.html'
    context_object_name = 'document'

    def get_object(self):
        # Try to get document from cache first
        document = self.get_document_from_cache(self.kwargs['category_path'], self.kwargs['document_slug'])
        if document:
            return document
        
        # Fallback: Get document with all optimizations in one query
        try:
            return Document.objects.select_related('category', 'category__parent', 'created_by')\
                .prefetch_related('versions', 'changelogs')\
                .get(slug=self.kwargs['document_slug'])
        except Document.DoesNotExist:
            raise Http404("Document not found")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        document = self.object

        # Use prefetched data (no additional queries)
        context['recent_versions'] = list(document.versions.all()[:5])
        context['recent_changes'] = list(document.changelogs.all()[:5])
        context['table_of_contents'] = document.generate_toc()

        # Optimized breadcrumb generation (cached)
        if not hasattr(self.request, '_breadcrumbs_cache'):
            self.request._breadcrumbs_cache = {}
        
        breadcrumb_key = f"breadcrumbs_{document.category.id}"
        if breadcrumb_key not in self.request._breadcrumbs_cache:
            self.request._breadcrumbs_cache[breadcrumb_key] = DocumentCategory.get_breadcrumbs(document.category)
        
        context['breadcrumbs'] = self.request._breadcrumbs_cache[breadcrumb_key]
        context['categories'] = self.get_categories_with_url_paths()

        return context


class VersionHistoryView(CategoryContextMixin, DocumentContextMixin, ListView):
    template_name = 'docvault/version_history.html'
    context_object_name = 'versions'
    paginate_by = 15

    def get_document(self):
        # Use request-level cache if available
        category = self.get_category_from_cache(self.kwargs['category_path'])
        if not category:
            category = DocumentCategory.get_by_path(self.kwargs['category_path'])
        
        if not category:
            raise Http404("Category not found")
        
        try:
            return Document.objects.select_related('category').get(
                category=category,
                slug=self.kwargs['document_slug']
            )
        except Document.DoesNotExist:
            raise Http404("Document not found")

    def get_queryset(self):
        self.document = self.get_document()
        return DocumentVersion.objects.filter(document=self.document).order_by('-version_number')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['document'] = self.document
        context['breadcrumbs'] = DocumentCategory.get_breadcrumbs(self.document.category)
        context['categories'] = self.get_categories_with_url_paths()
        return context


class DocumentVersionView(CategoryContextMixin, DocumentContextMixin, DetailView):
    template_name = 'docvault/document_version.html'
    context_object_name = 'version'

    def get_document(self):
        # Use request-level cache if available
        category = self.get_category_from_cache(self.kwargs['category_path'])
        if not category:
            category = DocumentCategory.get_by_path(self.kwargs['category_path'])
        
        if not category:
            raise Http404("Category not found")
        
        try:
            return Document.objects.select_related('category').get(
                category=category,
                slug=self.kwargs['document_slug']
            )
        except Document.DoesNotExist:
            raise Http404("Document not found")

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
        original_content = self.document.content
        self.document.content = self.object.content
        context['table_of_contents'] = self.document.generate_toc()
        self.document.content = original_content  # Restore original content

        # Get previous and next versions if they exist
        current_version = self.object.version_number
        context['previous_version'] = DocumentVersion.objects.filter(
            document=self.document,
            version_number__lt=current_version
        ).select_related('created_by').order_by('-version_number').first()

        context['next_version'] = DocumentVersion.objects.filter(
            document=self.document,
            version_number__gt=current_version
        ).select_related('created_by').order_by('version_number').first()

        # Get changelog for this version if exists
        try:
            context['changelog'] = Changelog.objects.select_related('created_by').get(version=self.object)
        except Changelog.DoesNotExist:
            context['changelog'] = None

        context['breadcrumbs'] = DocumentCategory.get_breadcrumbs(self.document.category)
        context['categories'] = self.get_categories_with_url_paths()

        return context


class DocumentChangelogView(CategoryContextMixin, DocumentContextMixin, ListView):
    template_name = 'docvault/document_changelog.html'
    context_object_name = 'changelogs'
    paginate_by = 15

    def get_document(self):
        # Use request-level cache if available
        category = self.get_category_from_cache(self.kwargs['category_path'])
        if not category:
            category = DocumentCategory.get_by_path(self.kwargs['category_path'])
        
        if not category:
            raise Http404("Category not found")
        
        try:
            return Document.objects.select_related('category').get(
                category=category,
                slug=self.kwargs['document_slug']
            )
        except Document.DoesNotExist:
            raise Http404("Document not found")

    def get_queryset(self):
        self.document = self.get_document()
        return Changelog.objects.filter(document=self.document).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['document'] = self.document
        context['breadcrumbs'] = DocumentCategory.get_breadcrumbs(self.document.category)
        context['categories'] = self.get_categories_with_url_paths()
        return context


class DocumentSearchView(CategoryContextMixin, ListView):
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
        context['categories'] = self.get_categories_with_url_paths()
        return context


class GlobalChangelogView(CategoryContextMixin, ListView):
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
        context['categories'] = self.get_categories_with_url_paths()
        return context


class DocumentCompareView(CategoryContextMixin, DocumentContextMixin, View):
    """Compare two versions of a document and show the differences"""
    template_name = 'docvault/document_compare.html'

    def get(self, request, **kwargs):
        # Use request-level cache if available
        category = self.get_category_from_cache(kwargs['category_path'])
        if not category:
            category = DocumentCategory.get_by_path(kwargs['category_path'])
        
        if not category:
            raise Http404("Category not found")
        
        document = get_object_or_404(Document, category=category, slug=kwargs['document_slug'])
        
        # Check if user wants to select versions
        select_mode = request.GET.get('select', 'false').lower() == 'true'
        
        # Get the two versions to compare
        version1_id = request.GET.get('v1')
        version2_id = request.GET.get('v2')
        
        if select_mode:
            # Show version selection form
            version1 = None
            version2 = None
        elif not version1_id or not version2_id:
            # Default to comparing current version with previous version
            versions = document.versions.all()[:2]
            if len(versions) >= 2:
                version1 = versions[1]  # Previous version
                version2 = versions[0]  # Current version
            else:
                version1 = version2 = versions[0] if versions else None
        else:
            # Get the specific versions to compare
            version1 = get_object_or_404(DocumentVersion, document=document, version_number=version1_id)
            version2 = get_object_or_404(DocumentVersion, document=document, version_number=version2_id)
        
        context = {
            'document': document,
            'version1': version1,
            'version2': version2,
            'versions': document.versions.all().order_by('-version_number'),
            'compare_mode': 'diff' if version1 and version2 else 'select',
            'breadcrumbs': DocumentCategory.get_breadcrumbs(document.category),
            'categories': self.get_categories_with_url_paths()
        }
        
        return render(request, self.template_name, context)


class SmartPathView(View):
    """Smart view that handles category paths only"""
    
    def get(self, request, category_path):
        # Check if this is a category path
        category = DocumentCategory.get_by_path(category_path)
        if category:
            # It's a category, show category view
            return DocumentListByCategoryView.as_view()(request, category_path=category_path)
        
        # If we get here, it's not found
        raise Http404("Category not found")


class SmartRouterView(View):
    """Smart view that routes to either category or document based on path analysis"""
    
    def get(self, request, path):
        # Clean the path
        path = path.strip('/')
        
        # Split the path into parts
        parts = [part for part in path.split('/') if part]
        
        if not parts:
            raise Http404("Invalid path")
        
        # OPTIMIZATION: Pre-fetch all categories and documents in one go
        # This eliminates the N+1 problem completely
        if not hasattr(request, '_prefetched_data'):
            # Get all categories with their relationships in a single query
            all_categories = DocumentCategory.objects.select_related('parent')\
                .prefetch_related('children', 'children__documents')\
                .annotate(
                    document_count=Count('documents'),
                    child_count=Count('children')
                )
            
            # Get all documents with their categories in a single query
            all_documents = Document.objects.select_related('category').all()
            
            # Build efficient lookups
            categories_by_path = {}
            categories_by_slug_parent = {}
            documents_by_category_slug = {}
            
            # Build category path lookup and pre-compute cached_url_path
            for category in all_categories:
                # Build the full path for this category
                path_parts = []
                current = category
                while current:
                    path_parts.insert(0, current.slug)
                    current = current.parent
                full_path = '/'.join(path_parts)
                categories_by_path[full_path] = category
                category.cached_url_path = full_path
                
                # Build slug+parent lookup for efficient path traversal
                key = (category.slug, category.parent_id)
                categories_by_slug_parent[key] = category
                
                # Pre-compute cached_url_path for children
                for subcategory in category.children.all():
                    path_parts = []
                    current = subcategory
                    while current:
                        path_parts.insert(0, current.slug)
                        current = current.parent
                    subcategory.cached_url_path = '/'.join(path_parts)
            
            # Build document lookup
            for document in all_documents:
                if document.category:
                    key = (document.category.id, document.slug)
                    documents_by_category_slug[key] = document
            
            request._prefetched_data = {
                'categories_by_path': categories_by_path,
                'categories_by_slug_parent': categories_by_slug_parent,
                'documents_by_category_slug': documents_by_category_slug,
                'all_categories': all_categories,
                'all_documents': all_documents
            }
        
        # Use the pre-fetched data
        data = request._prefetched_data
        
        # Check if this is a category path first
        if path in data['categories_by_path']:
            category = data['categories_by_path'][path]
            
            # Check if there's a document with this exact path
            if len(parts) > 1:
                # Try to find a document in the parent category
                parent_path = '/'.join(parts[:-1])
                if parent_path in data['categories_by_path']:
                    parent_category = data['categories_by_path'][parent_path]
                    document_key = (parent_category.id, parts[-1])
                    
                    if document_key in data['documents_by_category_slug']:
                        document = data['documents_by_category_slug'][document_key]
                        # It's a document, route to document detail
                        request._category_cache = {parent_path: parent_category}
                        request._document_cache = document
                        return DocumentDetailView.as_view()(request, category_path=parent_path, document_slug=parts[-1])
            
            # It's a category, route to category view
            request._category_cache = {path: category}
            return DocumentListByCategoryView.as_view()(request, category_path=path)
        
        # If no category found, try to find a document
        if len(parts) > 1:
            parent_path = '/'.join(parts[:-1])
            
            if parent_path in data['categories_by_path']:
                parent_category = data['categories_by_path'][parent_path]
                document_key = (parent_category.id, parts[-1])
                
                if document_key in data['documents_by_category_slug']:
                    document = data['documents_by_category_slug'][document_key]
                    # It's a document, route to document detail
                    request._category_cache = {parent_path: parent_category}
                    request._document_cache = document
                    return DocumentDetailView.as_view()(request, category_path=parent_path, document_slug=parts[-1])
        
        # If we get here, nothing was found
        raise Http404("Category or document not found")
from django.db.models import Count
from .models import DocumentCategory


class CategoryContextMixin:
    """Mixin to provide category context with cached URL paths"""
    
    def get_categories_with_url_paths(self):
        """Get all root categories with computed URL paths"""
        # Use pre-fetched data if available (from SmartRouterView)
        if hasattr(self.request, '_prefetched_data'):
            # Use the pre-fetched categories that already have cached_url_path computed
            return [cat for cat in self.request._prefetched_data['all_categories'] if cat.parent is None]
        
        # Fallback: fetch and compute URL paths
        categories = DocumentCategory.objects.filter(parent=None)\
            .prefetch_related('children', 'children__documents')\
            .annotate(
                document_count=Count('documents'),
                child_count=Count('children')
            )
        
        self._compute_url_paths(categories)
        return categories
    
    def _compute_url_paths(self, categories):
        """Compute cached_url_path for categories and their children"""
        for category in categories:
            # Build path from the already-fetched parent data
            path_parts = []
            current = category
            while current:
                path_parts.insert(0, current.slug)
                current = getattr(current, 'parent', None)
            category.cached_url_path = '/'.join(path_parts)
            
            # Do the same for children
            for subcategory in category.children.all():
                path_parts = []
                current = subcategory
                while current:
                    path_parts.insert(0, current.slug)
                    current = getattr(current, 'parent', None)
                subcategory.cached_url_path = '/'.join(path_parts)


class DocumentContextMixin:
    """Mixin to provide document-related context"""
    
    def get_document_from_cache(self, category_path, document_slug):
        """Get document using cached data if available"""
        # Use pre-fetched data if available (from SmartRouterView)
        if hasattr(self.request, '_prefetched_data') and hasattr(self.request, '_document_cache'):
            cached_document = self.request._document_cache
            if cached_document.slug == document_slug:
                # Document was already found and cached, but we need to add the prefetches
                from .models import Document
                return Document.objects.select_related('category', 'category__parent', 'created_by')\
                    .prefetch_related('versions', 'changelogs')\
                    .get(id=cached_document.id)
        
        # Use cached category if available (from SmartRouterView)
        if hasattr(self.request, '_category_cache'):
            category = self.request._category_cache.get(category_path)
            if category:
                from .models import Document
                try:
                    return Document.objects.select_related('category', 'category__parent', 'created_by')\
                        .prefetch_related('versions', 'changelogs')\
                        .get(category=category, slug=document_slug)
                except Document.DoesNotExist:
                    from django.http import Http404
                    raise Http404("Document not found")
        
        return None
    
    def get_category_from_cache(self, category_path):
        """Get category using cached data if available"""
        if hasattr(self.request, '_category_cache'):
            return self.request._category_cache.get(category_path)
        return None 
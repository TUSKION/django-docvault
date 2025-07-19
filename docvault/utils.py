from django.db.models import Count
from .models import DocumentCategory, Document


def get_optimized_categories_queryset():
    """Get optimized queryset for categories with counts and relationships"""
    return DocumentCategory.objects.filter(parent=None)\
        .prefetch_related('children', 'children__documents')\
        .annotate(
            document_count=Count('documents'),
            child_count=Count('children')
        )


def compute_url_paths(categories):
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


def get_documents_for_category(category, use_prefetched_data=False, prefetched_documents=None):
    """Get documents for a category, optionally using pre-fetched data"""
    if use_prefetched_data and prefetched_documents:
        # Filter pre-fetched documents for this category
        documents = [doc for doc in prefetched_documents if doc.category_id == category.id]
        # Sort by updated_at (descending)
        documents.sort(key=lambda x: x.updated_at, reverse=True)
        
        # Pre-compute URL paths for document categories
        for document in documents:
            if document.category:
                path_parts = []
                current = document.category
                while current:
                    path_parts.insert(0, current.slug)
                    current = getattr(current, 'parent', None)
                document.category.cached_url_path = '/'.join(path_parts)
        
        return documents
    
    # Fallback: query database
    documents = Document.objects.filter(category=category)\
        .select_related('category', 'category__parent', 'created_by')\
        .order_by('-updated_at')
    
    # Pre-compute URL paths for document categories
    for document in documents:
        if document.category:
            path_parts = []
            current = document.category
            while current:
                path_parts.insert(0, current.slug)
                current = getattr(current, 'parent', None)
            document.category.cached_url_path = '/'.join(path_parts)
    
    return documents 
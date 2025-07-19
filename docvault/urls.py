from django.urls import path, re_path, register_converter
from django.views.generic import TemplateView
from .views import (
    DocumentListView, DocumentDetailView, CategoryListView,
    DocumentListByCategoryView, VersionHistoryView, DocumentVersionView,
    DocumentChangelogView, DocumentSearchView, GlobalChangelogView,
    DocumentCompareView, SmartRouterView
)

# Custom path converter that handles slash-separated paths
class CategoryPathConverter:
    regex = '[a-z0-9\-]+(?:/[a-z0-9\-]+)*'
    
    def to_python(self, value):
        return value
    
    def to_url(self, value):
        return value

# Custom path converter that validates document exists
class DocumentSlugConverter:
    regex = '[a-z0-9\-]+'
    
    def to_python(self, value):
        return value
    
    def to_url(self, value):
        return value

register_converter(CategoryPathConverter, 'category_path')
register_converter(DocumentSlugConverter, 'docslug')

app_name = 'docvault'

urlpatterns = [
    # Global changelog
    path('changelog/', GlobalChangelogView.as_view(), name='global_changelog'),
    
    # Document listings
    path('', DocumentListView.as_view(), name='document_list'),
    path('search/', DocumentSearchView.as_view(), name='document_search'),

    # Category navigation
    path('categories/', CategoryListView.as_view(), name='category_list'),
    
    # Document action URLs - These MUST come first because they have specific endings
    re_path(
        r'^(?P<category_path>[a-z0-9\-]+(?:/[a-z0-9\-]+)*)/(?P<document_slug>[a-z0-9\-]+)/changelog/$', 
        DocumentChangelogView.as_view(), 
        name='document_changelog'
    ),
    re_path(
        r'^(?P<category_path>[a-z0-9\-]+(?:/[a-z0-9\-]+)*)/(?P<document_slug>[a-z0-9\-]+)/versions/$', 
        VersionHistoryView.as_view(), 
        name='version_history'
    ),
    re_path(
        r'^(?P<category_path>[a-z0-9\-]+(?:/[a-z0-9\-]+)*)/(?P<document_slug>[a-z0-9\-]+)/version/(?P<version_number>\d+)/$', 
        DocumentVersionView.as_view(), 
        name='document_version'
    ),
    re_path(
        r'^(?P<category_path>[a-z0-9\-]+(?:/[a-z0-9\-]+)*)/(?P<document_slug>[a-z0-9\-]+)/compare/$', 
        DocumentCompareView.as_view(), 
        name='document_compare'
    ),
    
    # Smart router - handles both categories and documents (MUST come last)
    re_path(
        r'^(?P<path>[a-z0-9\-]+(?:/[a-z0-9\-]+)*)/$',
        SmartRouterView.as_view(), 
        name='smart_router'
    ),
]
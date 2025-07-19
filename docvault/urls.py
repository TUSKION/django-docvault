from django.urls import path, re_path
from django.views.generic import TemplateView
from .views import (
    DocumentListView, DocumentDetailView, CategoryListView,
    DocumentListByCategoryView, VersionHistoryView, DocumentVersionView,
    DocumentChangelogView, DocumentSearchView, GlobalChangelogView,
    DocumentCompareView
)

app_name = 'docvault'

urlpatterns = [
    # Global changelog
    path('changelog/', GlobalChangelogView.as_view(), name='global_changelog'),
    
    # Document listings
    path('', DocumentListView.as_view(), name='document_list'),
    path('search/', DocumentSearchView.as_view(), name='document_search'),

    # Category navigation
    path('categories/', CategoryListView.as_view(), name='category_list'),
    
    # Nested category paths - supports unlimited nesting
    re_path(r'^(?P<category_path>[a-z0-9\-/]+)/$', DocumentListByCategoryView.as_view(), name='document_list_by_category'),

    # Documents with nested category paths
    re_path(r'^(?P<category_path>[a-z0-9\-/]+)/(?P<document_slug>[a-z0-9\-]+)/$', DocumentDetailView.as_view(), name='document_detail'),
    re_path(r'^(?P<category_path>[a-z0-9\-/]+)/(?P<document_slug>[a-z0-9\-]+)/versions/$', VersionHistoryView.as_view(), name='version_history'),
    re_path(r'^(?P<category_path>[a-z0-9\-/]+)/(?P<document_slug>[a-z0-9\-]+)/version/(?P<version_number>\d+)/$', DocumentVersionView.as_view(), name='document_version'),
    re_path(r'^(?P<category_path>[a-z0-9\-/]+)/(?P<document_slug>[a-z0-9\-]+)/changelog/$', DocumentChangelogView.as_view(), name='document_changelog'),
    re_path(r'^(?P<category_path>[a-z0-9\-/]+)/(?P<document_slug>[a-z0-9\-]+)/compare/$', DocumentCompareView.as_view(), name='document_compare'),
]

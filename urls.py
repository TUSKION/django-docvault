from django.urls import path
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
    path('<slug:category_slug>/', DocumentListByCategoryView.as_view(), name='document_list_by_category'),

    # Documents with category
    path('<slug:category_slug>/<slug:document_slug>/', DocumentDetailView.as_view(), name='document_detail'),
    path('<slug:category_slug>/<slug:document_slug>/versions/', VersionHistoryView.as_view(), name='version_history'),
    path('<slug:category_slug>/<slug:document_slug>/version/<int:version_number>/', DocumentVersionView.as_view(), name='document_version'),
    path('<slug:category_slug>/<slug:document_slug>/changelog/', DocumentChangelogView.as_view(), name='document_changelog'),
    path('<slug:category_slug>/<slug:document_slug>/compare/', DocumentCompareView.as_view(), name='document_compare'),
]

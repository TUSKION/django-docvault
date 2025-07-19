from django.contrib import admin
from django.conf import settings
from django import forms
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import DocumentCategory, Document, DocumentVersion, Changelog

class DocumentAdminForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        editor_setting = getattr(settings, 'DOCVAULT_EDITOR', 'text')
        
        if editor_setting == 'tinymce':
            try:
                from tinymce.widgets import TinyMCE
                self.fields['content'].widget = TinyMCE()
            except ImportError:
                # Fallback to regular textarea if TinyMCE is not installed
                pass
        elif editor_setting == 'meditor':
            try:
                from meditor.widgets import RichMarkdownWidget
                self.fields['content'].widget = RichMarkdownWidget(auto_convert_html=False)
                self.fields['content'].help_text = 'Write your document content in Markdown format. Use the toolbar for quick formatting. HTML auto-conversion is disabled by default.'
            except ImportError:
                # Fallback to regular textarea if meditor is not installed
                pass

class DocumentVersionInline(admin.TabularInline):
    model = DocumentVersion
    extra = 0
    readonly_fields = ('version_number', 'created_at')
    fields = ('version_number', 'content', 'created_by', 'created_at')

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        editor_setting = getattr(settings, 'DOCVAULT_EDITOR', 'text')
        
        if editor_setting == 'tinymce':
            try:
                from tinymce.widgets import TinyMCE
                formset.form.base_fields['content'].widget = TinyMCE()
            except ImportError:
                # Fallback to regular textarea if TinyMCE is not installed
                pass
        elif editor_setting == 'meditor':
            try:
                from meditor.widgets import RichMarkdownWidget
                formset.form.base_fields['content'].widget = RichMarkdownWidget(auto_convert_html=False)
            except ImportError:
                # Fallback to regular textarea if meditor is not installed
                pass
        return formset

class ChangelogInline(admin.TabularInline):
    model = Changelog
    extra = 0
    fields = ('description', 'importance', 'show_in_global', 'created_by', 'created_at', 'version')
    readonly_fields = ('created_at',)

class DocumentCategoryAdminForm(forms.ModelForm):
    class Meta:
        model = DocumentCategory
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter parent choices to prevent circular references
        if self.instance.pk:
            # Exclude self and descendants from parent choices
            descendants = self.instance.get_descendants(include_self=True)
            self.fields['parent'].queryset = DocumentCategory.objects.exclude(
                pk__in=descendants.values_list('pk', flat=True)
            )

@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    form = DocumentCategoryAdminForm
    list_display = ('get_hierarchical_name', 'slug', 'get_full_path', 'depth', 'get_document_count', 'get_children_count')
    list_filter = ('depth', 'parent')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('path', 'depth', 'get_breadcrumb_trail')
    ordering = ('path',)
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'parent', 'description')
        }),
        ('Hierarchy Information', {
            'fields': ('path', 'depth', 'get_breadcrumb_trail'),
            'classes': ('collapse',)
        }),
    )
    
    def get_hierarchical_name(self, obj):
        """Display category name with proper indentation based on depth"""
        indent = "—" * obj.depth
        return format_html('<span style="margin-left: {}px">{}{}</span>', 
                          obj.depth * 20, indent, obj.name)
    get_hierarchical_name.short_description = 'Name'
    get_hierarchical_name.admin_order_field = 'name'
    
    def get_full_path(self, obj):
        """Display the materialized path"""
        return obj.path or '-'
    get_full_path.short_description = 'Path'
    get_full_path.admin_order_field = 'path'
    
    def get_document_count(self, obj):
        """Show number of documents in this category"""
        count = obj.documents.count()
        if count > 0:
            return format_html('<a href="{}?category__id__exact={}">{}</a>', 
                              reverse('admin:docvault_document_changelist'), obj.id, count)
        return '0'
    get_document_count.short_description = 'Documents'
    
    def get_children_count(self, obj):
        """Show number of child categories"""
        count = obj.children.count()
        if count > 0:
            return format_html('<a href="{}?parent__id__exact={}">{}</a>', 
                              reverse('admin:docvault_documentcategory_changelist'), obj.id, count)
        return '0'
    get_children_count.short_description = 'Children'
    
    def get_breadcrumb_trail(self, obj):
        """Display breadcrumb trail for the category"""
        breadcrumbs = obj.get_ancestors(include_self=True)
        if not breadcrumbs:
            return '-'
        
        trail = []
        for i, category in enumerate(breadcrumbs):
            if i == len(breadcrumbs) - 1:
                # Current category
                trail.append(f'<strong>{category.name}</strong>')
            else:
                # Ancestor category
                admin_url = reverse('admin:docvault_documentcategory_change', args=[category.id])
                trail.append(f'<a href="{admin_url}">{category.name}</a>')
        
        return mark_safe(' > '.join(trail))
    get_breadcrumb_trail.short_description = 'Breadcrumb Trail'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related for parent"""
        return super().get_queryset(request).select_related('parent')
    
    def save_model(self, request, obj, form, change):
        """Ensure path and depth are updated when saving"""
        super().save_model(request, obj, form, change)
        # The model's save method will handle path/depth updates

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    form = DocumentAdminForm
    list_display = ('title', 'get_category_breadcrumb', 'created_at', 'updated_at', 'get_version_count')
    list_filter = ('category', 'category__depth', 'created_at', 'updated_at')
    search_fields = ('title', 'content', 'category__name')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('updated_at', 'get_category_breadcrumb')
    inlines = [DocumentVersionInline, ChangelogInline]
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'category', 'content')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at', 'get_category_breadcrumb')
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing an existing object
            return self.readonly_fields + ('created_at',)
        return self.readonly_fields
    
    def get_category_breadcrumb(self, obj):
        """Display category with breadcrumb trail"""
        if not obj.category:
            return '-'
        
        breadcrumbs = obj.category.get_ancestors(include_self=True)
        trail = []
        for i, category in enumerate(breadcrumbs):
            if i == len(breadcrumbs) - 1:
                trail.append(f'<strong>{category.name}</strong>')
            else:
                admin_url = reverse('admin:docvault_documentcategory_change', args=[category.id])
                trail.append(f'<a href="{admin_url}">{category.name}</a>')
        
        return mark_safe(' > '.join(trail))
    get_category_breadcrumb.short_description = 'Category'
    
    def get_version_count(self, obj):
        """Show number of versions"""
        count = obj.versions.count()
        if count > 0:
            return format_html('<a href="{}?document__id__exact={}">{}</a>', 
                              reverse('admin:docvault_documentversion_changelist'), obj.id, count)
        return '0'
    get_version_count.short_description = 'Versions'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related for category"""
        return super().get_queryset(request).select_related('category', 'created_by')

@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ('document', 'version_number', 'get_document_category', 'created_at', 'created_by')
    list_filter = ('document__category', 'created_at')
    search_fields = ('document__title', 'content', 'document__category__name')
    readonly_fields = ('version_number', 'created_at')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        editor_setting = getattr(settings, 'DOCVAULT_EDITOR', 'text')
        
        if editor_setting == 'tinymce':
            try:
                from tinymce.widgets import TinyMCE
                form.base_fields['content'].widget = TinyMCE()
            except ImportError:
                # Fallback to regular textarea if TinyMCE is not installed
                pass
        elif editor_setting == 'meditor':
            try:
                from meditor.widgets import RichMarkdownWidget
                form.base_fields['content'].widget = RichMarkdownWidget(auto_convert_html=False)
            except ImportError:
                # Fallback to regular textarea if meditor is not installed
                pass
        return form
    
    def get_document_category(self, obj):
        """Display document category with breadcrumb"""
        if not obj.document.category:
            return '-'
        
        breadcrumbs = obj.document.category.get_ancestors(include_self=True)
        trail = []
        for i, category in enumerate(breadcrumbs):
            if i == len(breadcrumbs) - 1:
                trail.append(f'<strong>{category.name}</strong>')
            else:
                admin_url = reverse('admin:docvault_documentcategory_change', args=[category.id])
                trail.append(f'<a href="{admin_url}">{category.name}</a>')
        
        return mark_safe(' > '.join(trail))
    get_document_category.short_description = 'Category'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related('document__category', 'created_by')

@admin.register(Changelog)
class ChangelogAdmin(admin.ModelAdmin):
    list_display = ('document', 'get_document_category', 'get_version_number', 'importance', 'show_in_global', 'created_at', 'created_by')
    list_filter = ('importance', 'show_in_global', 'document__category', 'created_at')
    search_fields = ('document__title', 'description', 'document__category__name')
    readonly_fields = ('created_at',)
    
    def get_version_number(self, obj):
        return obj.version.version_number if obj.version else '-'
    get_version_number.short_description = 'Version'
    
    def get_document_category(self, obj):
        """Display document category with breadcrumb"""
        if not obj.document.category:
            return '-'
        
        breadcrumbs = obj.document.category.get_ancestors(include_self=True)
        trail = []
        for i, category in enumerate(breadcrumbs):
            if i == len(breadcrumbs) - 1:
                trail.append(f'<strong>{category.name}</strong>')
            else:
                admin_url = reverse('admin:docvault_documentcategory_change', args=[category.id])
                trail.append(f'<a href="{admin_url}">{category.name}</a>')
        
        return mark_safe(' > '.join(trail))
    get_document_category.short_description = 'Category'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related('document__category', 'created_by', 'version')
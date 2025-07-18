from django.contrib import admin
from django.conf import settings
from django import forms
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

@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description')

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    form = DocumentAdminForm
    list_display = ('title', 'category', 'created_at', 'updated_at')
    list_filter = ('category', 'created_at', 'updated_at')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('updated_at',)
    inlines = [DocumentVersionInline, ChangelogInline]
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'category', 'content')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing an existing object
            return self.readonly_fields + ('created_at',)
        return self.readonly_fields

@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ('document', 'version_number', 'created_at', 'created_by')
    list_filter = ('document', 'created_at')
    search_fields = ('document__title', 'content')
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

@admin.register(Changelog)
class ChangelogAdmin(admin.ModelAdmin):
    list_display = ('document', 'get_version_number', 'importance', 'show_in_global', 'created_at', 'created_by')
    list_filter = ('importance', 'show_in_global', 'document', 'created_at')
    search_fields = ('document__title', 'description')
    readonly_fields = ('created_at',)
    
    def get_version_number(self, obj):
        return obj.version.version_number if obj.version else '-'
    get_version_number.short_description = 'Version'
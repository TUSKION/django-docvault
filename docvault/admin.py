from django.contrib import admin
from .models import DocumentCategory, Document, DocumentVersion, Changelog

class DocumentVersionInline(admin.TabularInline):
    model = DocumentVersion
    extra = 0
    readonly_fields = ('version_number', 'created_at')
    fields = ('version_number', 'content', 'created_by', 'created_at')

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
    list_display = ('title', 'category', 'created_at', 'updated_at')
    list_filter = ('category', 'created_at', 'updated_at')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at', 'updated_at')
    inlines = [DocumentVersionInline, ChangelogInline]
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'category', 'content')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )

@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ('document', 'version_number', 'created_at', 'created_by')
    list_filter = ('document', 'created_at')
    search_fields = ('document__title', 'content')
    readonly_fields = ('version_number', 'created_at')

@admin.register(Changelog)
class ChangelogAdmin(admin.ModelAdmin):
    list_display = ('document', 'get_version_number', 'importance', 'show_in_global', 'created_at', 'created_by')
    list_filter = ('importance', 'show_in_global', 'document', 'created_at')
    search_fields = ('document__title', 'description')
    readonly_fields = ('created_at',)
    
    def get_version_number(self, obj):
        return obj.version.version_number if obj.version else '-'
    get_version_number.short_description = 'Version'
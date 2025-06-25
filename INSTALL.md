# Django DocVault Installation Guide

## Installation

You can install DocVault in three ways:

### 1. From PyPI (recommended)

```bash
pip install django-docvault
```

### 2. From Git repository

```bash
pip install git+https://github.com/yourusername/django-docvault.git
```

### 3. Manual installation

```bash
git clone https://github.com/yourusername/django-docvault.git
cd django-docvault
pip install -e .
```

## Configuration

### 1. Add to INSTALLED_APPS

Add `'docvault'` and `'tinymce'` to your `INSTALLED_APPS` in settings.py:

```python
INSTALLED_APPS = [
    # ...
    'tinymce',
    'docvault',
    # ...
]
```

### 2. Configure TinyMCE (optional)

You can add TinyMCE configuration to your settings.py:

```python
TINYMCE_DEFAULT_CONFIG = {
    'height': 360,
    'width': 'auto',
    'menubar': False,
    'plugins': 'link image lists table code',
    'toolbar': 'undo redo | formatselect | bold italic underline | alignleft aligncenter alignright | bullist numlist | outdent indent | table | link image | code',
    'custom_undo_redo_levels': 10,
}
```

### 3. Configure URLs

Add DocVault URLs to your project's urls.py:

```python
from django.urls import include, path

urlpatterns = [
    # ...
    path('docs/', include('docvault.urls', namespace='docvault')),
    path('tinymce/', include('tinymce.urls')),
    # ...
]
```

Note: Make sure your project is configured to use namespaces in URLs. For Django 4.2+, this is the standard approach.

### 4. Run Migrations

```bash
python manage.py migrate docvault
```

### 5. Collect Static Files (for production)

```bash
python manage.py collectstatic
```

## Template Customization

DocVault templates can be overridden by creating your own versions in your project:

1. Create a directory structure in your project's templates folder:
   ```
   templates/
   └── docvault/
       └── your_template.html
   ```

2. Copy the original template and customize it as needed.

Available templates to override:
- base.html
- document_list.html
- document_detail.html
- category_list.html
- version_history.html
- document_version.html
- document_changelog.html
- search_results.html

## Usage

After installation, you can:

1. Access the admin interface to create document categories and documents
2. View documents at `/docs/` (or your configured URL)
3. Search for documents
4. View document version history and changelogs

## Requirements

- Django 4.2 or higher
- Python 3.11 or higher
- django-tinymce 3.4.0 or higher

## Troubleshooting

If you encounter issues:

1. Ensure all migrations have been applied
2. Check that 'docvault' and 'tinymce' are in INSTALLED_APPS
3. Verify URL configuration includes both docvault and tinymce URLs
4. Make sure TinyMCE static files are properly collected

For more help, refer to the [GitHub repository](https://github.com/yourusername/django-docvault).
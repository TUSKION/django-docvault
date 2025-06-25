# DocVault

DocVault is a Django application for managing documents with version history, changelogs, and categorization.

## Features

- Document management with rich text content (TinyMCE)
- Automatic versioning system (tracks changes to document content)
- Document categorization
- Search functionality
- Table of contents generation
- Clean URL structure
- Responsive design

## URLs

Documents are accessible at:
- `/docs/` - Main document list
- `/docs/search/` - Document search
- `/docs/changelog/` - Global changelog
- `/docs/categories/` - List of categories
- `/docs/<category-slug>/` - Documents in a specific category
- `/docs/<category-slug>/<document-slug>/` - View a specific document
- `/docs/<category-slug>/<document-slug>/versions/` - Version history
- `/docs/<category-slug>/<document-slug>/version/<version-number>/` - Specific document version
- `/docs/<category-slug>/<document-slug>/changelog/` - Document changelog
- `/docs/<category-slug>/<document-slug>/compare/` - Document comparison

## Template Overriding

DocVault is designed to allow easy template customization. To override any template:

1. Create a directory structure in your project's main templates folder:
   ```
   templates/
   └── docvault/
       └── your_template.html
   ```

2. Copy the original template from `docvault/templates/docvault/` to your new location.

3. Modify the template as needed.

Django's template loading system will automatically use your overridden template instead of the default one.

### Available Templates

The following templates can be overridden:

- **base.html** - Base template with layout structure
- **document_list.html** - List of all documents
- **document_detail.html** - Single document view with content
- **category_list.html** - List of all categories
- **version_history.html** - Document version history
- **document_version.html** - Single version view
- **document_changelog.html** - Document changelog
- **document_compare.html** - Document comparison view
- **global_changelog.html** - Global changelog view
- **search_results.html** - Search results page

### Example: Overriding document_detail.html

1. Create the file at `templates/docvault/document_detail.html`
2. Copy the content from the original template
3. Customize as needed, keeping the template block structure

## Table of Contents

The table of contents is automatically generated from headings in the document content. 
The system scans for HTML heading tags (h1-h6) and creates a clickable navigation structure.

You can customize the TOC display by overriding the `document_detail.html` template.

## Search Functionality

The search feature looks for matches in both document titles and content.
To customize the search results display, override the `search_results.html` template.

## Models

- **DocumentCategory** - Categories for organizing documents
- **Document** - Core document model with content and metadata
- **DocumentVersion** - Stores version history of documents
- **Changelog** - Records changes made to documents

## Requirements

- Django 3.2+
- TinyMCE for rich text editing

## License

This project is licensed under the MIT License.
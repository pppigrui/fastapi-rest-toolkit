# Admin System Status And Roadmap

This document records what has already been implemented for the Django-admin-like management system and what remains to be built.

## Goal

Provide a model-driven admin system for FastAPI REST Toolkit:

- register SQLAlchemy models with Python configuration
- generate CRUD admin APIs automatically
- provide a built-in management UI
- keep frontend code separate from `admin.py`
- use Vue 3, JavaScript, and Element Plus
- follow a layout/style similar to the existing admin screenshot

## Technical Baseline

Backend:

- Python
- FastAPI
- SQLAlchemy async models
- `sqlalchemy-crud-plus`
- Pydantic v2
- existing `ViewSet`, `CRUDService`, filters, pagination, authentication, and permissions

Frontend:

- Vue 3
- JavaScript
- Element Plus
- Element Plus Icons
- local Font Awesome assets
- static files served by FastAPI
- no CDN dependency
- no frontend build step

Main files:

```text
src/fastapi_rest_toolkit/admin.py
src/fastapi_rest_toolkit/admin_frontend/index.html
src/fastapi_rest_toolkit/admin_frontend/assets/js/api.js
src/fastapi_rest_toolkit/admin_frontend/assets/js/app.js
src/fastapi_rest_toolkit/admin_frontend/assets/js/icons.js
src/fastapi_rest_toolkit/admin_frontend/assets/js/utils.js
src/fastapi_rest_toolkit/admin_frontend/assets/css/
```

## Implemented

### Admin Core

- Added `AdminSite`.
- Added `ModelAdmin`.
- Added `AdminSite.register(...)`.
- Added generated admin CRUD routes under `/admin/api`.
- Added `/admin/api/meta`.
- Reused existing `ViewSet` and `CRUDService`.
- Reused existing pagination, search, ordering, authentication, and permission primitives.
- Exported admin APIs from package entrypoint.

### Built-In Frontend

- Added Vue 3 + JavaScript + Element Plus admin page.
- Moved frontend code into `src/fastapi_rest_toolkit/admin_frontend/`.
- Split frontend code into:
  - `api.js`
  - `app.js`
  - `icons.js`
  - `utils.js`
- Split CSS into:
  - `tokens.css`
  - `base.css`
  - `layout.css`
  - `components.css`
  - `responsive.css`
- Served Vue, Element Plus, Element Plus Icons, and Font Awesome from local static assets.
- Removed CDN dependency.

### Layout And UX

- Dark sidebar.
- Header with breadcrumb and search.
- Tabs strip.
- Query/filter area.
- Table toolbar.
- Data table.
- Summary side panel.
- Drawer for create/edit/detail.
- Element Plus success/error messages.
- Element Plus confirmation dialogs.

### Model Metadata

- `label`
- `group`
- `resource`
- `list_display`
- `search_fields`
- `list_filter`
- `ordering_fields`
- `readonly_fields`
- `allowed_actions`
- `fieldsets`
- `actions`
- `display_methods`
- `list_editable`
- `config_meta`

### Field Metadata

- Field labels use SQLAlchemy column `info["name"]` when present.
- Falls back to field name when `info["name"]` is missing.
- Field metadata includes:
  - name
  - label
  - type
  - primary key flag
  - nullable flag
  - readonly flag
  - default flag
  - max length
  - choices
  - computed flag
  - field config

### `config_meta`

Implemented model-level config:

- `icon`
- `fields`

Implemented field-level config:

- `hidden`
- `table_hidden`
- `form_hidden`
- `detail_hidden`
- `placeholder`
- `widget`
- `help_text`
- `width`
- `rules`
- `choices`
- `resource`
- `label_field`
- `value_field`
- `search_fields`
- `limit`

Supported widgets:

- `input`
- `textarea`
- `switch`
- `number`
- `select`
- `autocomplete`
- `date`
- `datetime`

### List Page

- Generated table columns from `list_display`.
- Search from `search_fields`.
- Exact filters from `list_filter`.
- Boolean filter rendered as yes/no select.
- Relation select filter rendered from another admin resource.
- Choice filter rendered as select controls.
- Date/datetime filters rendered as range pickers.
- Range filters mapped to `field__gte` and `field__lte`.
- Header sorting from `ordering_fields`.
- Calculated display columns from `display_methods`.
- Inline list editing for fields declared in `list_editable`.
- Explicit save/revert controls for list edit drafts.
- Pagination.
- Refresh.
- Row selection.
- Single-row actions:
  - view
  - edit
  - delete
- Batch delete selected rows.
- Custom bulk actions.
- Custom row actions.

### Forms

- Create drawer.
- Edit drawer.
- Read-only detail drawer.
- Fieldsets for create/edit/detail drawers.
- `readonly_fields` excluded from create/edit forms.
- `form_hidden` support.
- `detail_hidden` support.
- Input/textarea/switch/number/select/autocomplete/date/datetime widgets.
- Relation select fields using another admin resource.
- Remote autocomplete fields using another admin resource.
- Choice fields and SQLAlchemy Enum fields using select widgets.
- Choice labels rendered in table/detail tags.
- Form validation from Element Plus `rules`.
- Default required validation for editable non-null fields without defaults.

### Demo

Demo admin registers:

- `User`
- `Post`

Demo examples include:

- Chinese field labels via `Column.info["name"]`
- Font Awesome menu icons
- email validation
- switch field
- textarea field
- relation select field
- fieldsets
- custom admin actions
- declarative choices
- list filters
- ordering fields
- readonly fields
- calculated display columns
- list editable fields

## Current Usage Example

```python
admin = AdminSite(get_session=get_session, title="FastAPI REST Toolkit 管理后台")

admin.register(
    User,
    label="用户管理",
    group="Demo",
    list_display=("id", "name", "email", "is_active", "created_at"),
    search_fields=("name", "email"),
    list_filter=("is_active",),
    ordering_fields=("id", "name", "email", "created_at"),
    readonly_fields=("id", "created_at"),
    config_meta={
        "icon": "fa-solid fa-user",
        "fields": {
            "email": {
                "placeholder": "请输入邮箱",
                "width": 220,
                "rules": [
                    {"required": True, "message": "请输入邮箱", "trigger": "blur"},
                    {"type": "email", "message": "请输入正确的邮箱", "trigger": "blur"},
                ],
            },
            "is_active": {
                "widget": "switch",
                "width": 120,
            },
            "created_at": {
                "form_hidden": True,
                "width": 180,
            },
        },
    },
)

admin.register(
    Post,
    label="文章管理",
    group="Demo",
    list_display=("id", "title", "author_id", "created_at"),
    search_fields=("title", "content"),
    list_filter=("author_id",),
    ordering_fields=("id", "title", "author_id", "created_at"),
    readonly_fields=("id", "created_at"),
    config_meta={
        "icon": "fa-solid fa-file-lines",
        "fields": {
            "author_id": {
                "widget": "select",
                "resource": "users",
                "label_field": "name",
                "placeholder": "请选择作者",
                "width": 150,
                "rules": [
                    {"required": True, "message": "请选择作者", "trigger": "change"},
                ],
            },
            "content": {
                "widget": "textarea",
                "table_hidden": True,
                "placeholder": "请输入正文内容",
                "help_text": "长文本字段适合使用 textarea。",
            },
            "created_at": {
                "form_hidden": True,
                "width": 180,
            },
        },
    },
)

app.include_router(admin.router, prefix="/admin")
```

## Remaining Work

### 1. Inline Models

Manage related child resources inside parent detail/edit workflows.

Examples:

- User detail displays related Posts
- Parent edit can include child table

### 2. Import And Advanced Export

CSV export is implemented. Remaining import/export work:

- CSV import
- Excel export/import
- field selection
- validation report
- import preview

### 3. Object History

Track admin changes.

Expected behavior:

- who changed object
- when it changed
- old/new values where feasible
- history view from detail drawer/page

### 4. Dashboard

Admin home page should show:

- app/model index
- model counts
- recent operations
- quick links

## Development Rules For Future Admin Work

- Keep UI code under `admin_frontend`.
- Keep Python route/metadata code in `admin.py`.
- Put new optional display/behavior config under `config_meta` unless it is a stable top-level admin API.
- Keep frontend files separated by responsibility.
- Do not add CDN dependencies.
- Do not add a frontend build step.
- Keep the UI dense and operational.
- Use Element Plus components.
- Show operation success/failure with Element Plus messages.
- Add confirmation dialogs for destructive actions.
- Verify with `rtk node --check` and `rtk python -m compileall`.
- Do not use `uv run` unless explicitly requested.
- Do not write tests unless explicitly requested.

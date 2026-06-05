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
- `resource`
- `label_field`
- `value_field`
- `limit`

Supported widgets:

- `input`
- `textarea`
- `switch`
- `number`
- `select`
- `date`
- `datetime`

### List Page

- Generated table columns from `list_display`.
- Search from `search_fields`.
- Exact filters from `list_filter`.
- Boolean filter rendered as yes/no select.
- Relation select filter rendered from another admin resource.
- Header sorting from `ordering_fields`.
- Pagination.
- Refresh.
- Row selection.
- Single-row actions:
  - view
  - edit
  - delete
- Batch delete selected rows.

### Forms

- Create drawer.
- Edit drawer.
- Read-only detail drawer.
- `readonly_fields` excluded from create/edit forms.
- `form_hidden` support.
- `detail_hidden` support.
- Input/textarea/switch/number/select/date/datetime widgets.
- Relation select fields using another admin resource.
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
- list filters
- ordering fields
- readonly fields

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

### 1. Fieldsets

Group fields in create/edit/detail drawers.

Suggested config:

```python
config_meta={
    "fieldsets": [
        {"label": "基础信息", "fields": ["name", "email"]},
        {"label": "状态", "fields": ["is_active"]},
        {"label": "时间", "fields": ["created_at"]},
    ]
}
```

Expected behavior:

- create/edit form renders grouped sections
- detail view renders grouped sections
- fields not listed in fieldsets can fall back to an "其他" section

### 2. Custom Actions

Support Django-admin-like model actions.

Initial scope:

- model-level batch actions
- row-level actions
- Element Plus confirmation
- success/error result display

Suggested config:

```python
actions=("delete_selected", "activate_selected")
```

Later scope:

- custom backend endpoints
- action metadata in `/admin/api/meta`
- action permissions

### 3. Remote Autocomplete

Current `select` loads up to 100 options. Large tables need remote search.

Suggested config:

```python
"author_id": {
    "widget": "autocomplete",
    "resource": "users",
    "label_field": "name",
    "search_fields": ["name", "email"],
}
```

Expected behavior:

- remote query while typing
- debounce
- loading state
- selected value display

### 4. Date Range Filters

Extend `list_filter` for date and datetime fields.

Expected behavior:

- date/datetime filter renders range picker
- backend accepts range query parameters
- query operators map cleanly to `sqlalchemy-crud-plus`

### 5. Choices And Enums

Support declarative choices.

Suggested config:

```python
"status": {
    "choices": [
        {"label": "启用", "value": "active"},
        {"label": "禁用", "value": "disabled"},
    ]
}
```

Expected behavior:

- form renders select
- table/detail can render label
- optional tag style
- list filter can use choices

### 6. Permissions

Admin UI must eventually reflect backend permissions.

Needed permissions:

- view
- create
- update
- delete
- action

Rules:

- frontend can hide unavailable controls
- backend must still enforce permissions

### 7. Inline Models

Manage related child resources inside parent detail/edit workflows.

Examples:

- User detail displays related Posts
- Parent edit can include child table

This should be implemented after fieldsets and custom actions.

### 8. Import And Export

Start with CSV.

Later:

- Excel export/import
- field selection
- validation report
- import preview

### 9. Object History

Track admin changes.

Expected behavior:

- who changed object
- when it changed
- old/new values where feasible
- history view from detail drawer/page

### 10. Dashboard

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


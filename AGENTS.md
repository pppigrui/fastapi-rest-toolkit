# RTK - Rust Token Killer (Codex CLI)

**Usage**: Token-optimized CLI proxy for shell commands.

## Shell Rule

Always prefix shell commands with `rtk`.

Examples:

```bash
rtk git status
rtk python -m compileall src demo
rtk node --check src/fastapi_rest_toolkit/admin_frontend/assets/js/app.js
```

Do not use `uv run` for verification unless the user explicitly asks for it.

## Testing Rule

默认不写测试用例，除非用户明确要求。

For verification, prefer lightweight checks:

```bash
rtk node --check src/fastapi_rest_toolkit/admin_frontend/assets/js/app.js
rtk node --check src/fastapi_rest_toolkit/admin_frontend/assets/js/api.js
rtk node --check src/fastapi_rest_toolkit/admin_frontend/assets/js/utils.js
rtk python -m compileall src demo
```

## Project Tech Stack

- Backend language: Python.
- Backend framework: FastAPI.
- ORM/model layer: SQLAlchemy async models.
- CRUD foundation: `sqlalchemy-crud-plus`.
- Schema layer: Pydantic v2.
- Admin frontend language: JavaScript.
- Admin frontend framework: Vue 3.
- Admin UI component library: Element Plus.
- Icons: Element Plus Icons and local Font Awesome assets.
- Styling: plain CSS split by responsibility.
- Package layout: source code lives under `src/fastapi_rest_toolkit/`.

Do not introduce TypeScript, React, a build step, or a frontend bundler for the built-in admin unless the user explicitly asks for a redesign.

## Admin Architecture

The admin system is Django-admin-like but must stay native to this project.

- `src/fastapi_rest_toolkit/admin.py` owns admin registration, metadata, route generation, and static asset serving.
- `AdminSite` owns the admin router and registered models.
- `ModelAdmin` owns per-model configuration.
- Generated admin CRUD routes must reuse the existing `ViewSet`, `CRUDService`, schema generation, filters, pagination, authentication, and permissions.
- The admin frontend must live under `src/fastapi_rest_toolkit/admin_frontend/`.
- Do not embed Vue, CSS, or large frontend templates directly in `admin.py`.
- Frontend assets must be served locally. Do not depend on CDN resources.

Current frontend structure:

```text
src/fastapi_rest_toolkit/admin_frontend/
  index.html
  assets/
    css/
      tokens.css
      base.css
      layout.css
      components.css
      responsive.css
    js/
      api.js
      app.js
      icons.js
      utils.js
    vendor/
```

## Admin UI Direction

Use the existing screenshot-inspired admin layout as the visual baseline:

- dark left sidebar
- compact top header
- breadcrumb and tabs area
- query/filter card
- toolbar
- dense data table
- drawer-based create/edit/detail workflows

The aesthetic direction is industrial/utilitarian: quiet, dense, operational, and efficient. Avoid landing-page styling, oversized hero sections, decorative card-heavy layouts, gradient-orb decoration, and marketing copy.

Use Element Plus components for controls:

- `el-table` for lists
- `el-form` and `el-form-item` for forms
- `el-drawer` for create/edit/detail
- `el-select` for choices and relation fields
- `el-date-picker` for date/datetime fields
- `el-message` and `el-message-box` for success/error/confirmation
- `el-pagination` for paging

## Configuration Design

Prefer Python-side declarative configuration on `admin.register(...)`.

Top-level model options currently include:

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

All optional frontend behavior that is not a stable top-level admin API should go under `config_meta`.

Example:

```python
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
            "is_active": {"widget": "switch", "width": 120},
            "created_at": {"form_hidden": True, "width": 180},
        },
    },
)
```

Field labels should use SQLAlchemy column `info["name"]` when present. If not set, use the Python field name.

Supported field config keys:

- `hidden`: hide from table, form, and detail
- `table_hidden`: hide from table only
- `form_hidden`: hide from create/edit form only
- `detail_hidden`: hide from detail view only
- `placeholder`: input placeholder
- `widget`: `input`, `textarea`, `switch`, `number`, `select`, `date`, or `datetime`
- `help_text`: helper text under a form field
- `width`: table column width
- `rules`: Element Plus form validation rules
- `resource`: option source resource for `select`
- `label_field`: option label field for `select`
- `value_field`: option value field for `select`; default is target resource primary key
- `limit`: option loading limit for `select`; default is `100`

## Current Admin Capabilities

Implemented:

- model registration via `AdminSite.register()`
- generated admin CRUD routes under `/admin/api`
- built-in Vue 3 + JavaScript + Element Plus admin page
- local static assets; no CDN dependency
- dark sidebar/topbar/table layout
- metadata endpoint `/admin/api/meta`
- grouped menu from registered models
- menu icons via `config_meta["icon"]`
- field labels from SQLAlchemy `Column.info["name"]`
- list display columns
- search fields
- `list_filter`
- `ordering_fields` and table header sorting
- pagination
- create/edit drawer
- detail/read-only drawer
- delete single row
- batch delete by selected rows
- Element Plus success/error/confirmation messages
- field-level visibility config
- field-level placeholder/help text/width
- form validation rules via `config_meta.fields.*.rules`
- default required rules for non-null editable fields without defaults
- widgets: input, textarea, switch, number, select, date, datetime
- relation select fields using another admin resource

## Admin Roadmap

Planned next features should be implemented incrementally:

1. Fieldsets: group create/edit/detail fields into sections.
2. Custom actions: support model-level and row-level actions beyond delete.
3. Remote autocomplete: searchable relation selector for large tables.
4. Date range filters: list filtering for date/datetime ranges.
5. Choices/enums: declarative options and tag rendering.
6. Permissions: view/create/update/delete/action permissions in backend and UI.
7. Inline models: manage child resources inside a parent detail view.
8. Import/export: CSV first, Excel later if needed.
9. Object history/audit log.
10. Dashboard: grouped model index, counts, recent operations.

## Engineering Guidelines

Before coding:

- State assumptions when unclear.
- If a request can be interpreted multiple ways, ask before implementing.
- Prefer small, verifiable increments.

Implementation:

- Touch only files required for the requested change.
- Match existing code style.
- Avoid speculative abstractions.
- Keep frontend JS/CSS separated by responsibility.
- Keep admin UI logic out of `admin.py`.
- Prefer existing project primitives over new dependencies.
- Do not remove unrelated files or changes.

Verification:

- Use `rtk`.
- Do not use `uv run` unless explicitly requested.
- Do not write tests unless explicitly requested.
- Run syntax/compile checks relevant to changed files.
- If a browser/runtime check is blocked by local dependencies, state the blocker clearly.

Git/worktree:

- The worktree may already contain user changes.
- Never revert unrelated user changes.
- Do not run destructive git commands unless the user explicitly asks.


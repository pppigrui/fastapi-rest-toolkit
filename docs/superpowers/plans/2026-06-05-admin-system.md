# Admin System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Django-admin-like model registration system that can generate admin CRUD APIs and a built-in management page from SQLAlchemy models.

**Architecture:** Introduce `ModelAdmin` for per-model configuration and `AdminSite` for registration and route generation. Reuse the existing `ViewSet`, `CRUDService`, schema generation, filters, pagination, and permissions instead of creating a separate CRUD stack. Keep the admin frontend in `src/fastapi_rest_toolkit/admin_frontend/` instead of embedding UI code in Python.

**Tech Stack:** FastAPI, SQLAlchemy async models, sqlalchemy-crud-plus, Pydantic v2, Vue 3, JavaScript, Element Plus, CSS served by FastAPI.

---

### Task 1: Admin Core

**Files:**
- Create: `src/fastapi_rest_toolkit/admin.py`
- Modify: `src/fastapi_rest_toolkit/__init__.py`

- [ ] Create `ModelAdmin` with list, search, ordering, readonly, label, group, and CRUD action options.
- [ ] Create `AdminSite.register()` to store model registrations.
- [ ] Generate one internal `ViewSet` per registered model.
- [ ] Expose `AdminSite.router` with metadata and CRUD routes.

### Task 2: Built-in Admin Page

**Files:**
- Modify: `src/fastapi_rest_toolkit/admin.py`
- Create: `src/fastapi_rest_toolkit/admin_frontend/index.html`
- Create: `src/fastapi_rest_toolkit/admin_frontend/app.js`
- Create: `src/fastapi_rest_toolkit/admin_frontend/styles.css`

- [ ] Add `GET /` route returning a single-page admin interface.
- [ ] Use the screenshot-inspired layout: dark sidebar, top bar, tabs, query area, toolbar, table, and modal form.
- [ ] Drive menus, columns, and forms from `/api/meta`.
- [ ] Implement the page with Vue 3, JavaScript, and Element Plus in the dedicated frontend folder.

### Task 3: Demo Wiring

**Files:**
- Modify: `demo/main.py`
- Modify: `README.md`

- [ ] Register `User` and `Post` in `AdminSite`.
- [ ] Include the admin router at `/admin`.
- [ ] Document the minimal usage snippet.

### Task 4: Verification

**Files:**
- No test files by default, per project instruction.

- [ ] Run import/compile checks.
- [ ] Start the demo app if needed and verify route registration manually.

(function () {
  if (!window.Vue || !window.ElementPlus) {
    document.getElementById("app").innerHTML = `
      <div class="boot-error">
        <strong>管理后台资源加载失败</strong>
        <span>请确认本地 Vue 3 和 Element Plus 静态资源存在。</span>
      </div>
    `;
    throw new Error("Vue or Element Plus is not loaded");
  }

  const { createApp } = Vue;
  const icons = window.AdminIcons;
  const api = window.AdminApi;
  const utils = window.AdminUtils;

  createApp({
    components: icons,
    setup() {
      return icons;
    },
    data() {
      return {
        title: "管理后台",
        meta: { groups: [], models: [] },
        currentResource: "",
        openedResources: [],
        isSidebarCollapsed: true,
        isResourcePanelCollapsed: true,
        isQueryExpanded: false,
        filters: {},
        globalKeyword: "",
        rows: [],
        total: 0,
        pagination: {
          page: 1,
          pageSize: 20,
        },
        ordering: "",
        selectedRow: null,
        selectedRows: [],
        drawerVisible: false,
        drawerMode: "create",
        drawerTitle: "",
        formData: {},
        detailData: {},
        editingRow: null,
        relationOptions: {},
        relationLoading: {},
        listEditDrafts: {},
        loading: false,
        saving: false,
        exporting: false,
        listEditSaving: false,
      };
    },
    computed: {
      currentModel() {
        return this.meta.models.find((model) => model.resource === this.currentResource);
      },
      openedResourceTabs() {
        return this.openedResources
          .map((resource) => this.meta.models.find((model) => model.resource === resource))
          .filter(Boolean);
      },
      currentFields() {
        return this.currentModel?.fields || [];
      },
      searchableFields() {
        const names = new Set(this.currentModel?.search_fields || []);
        return this.currentFields.filter((field) => {
          const config = this.fieldConfig(field);
          return names.has(field.name) && !config.hidden;
        });
      },
      listFilterFields() {
        const names = new Set(this.currentModel?.list_filter || []);
        return this.currentFields.filter((field) => {
          const config = this.fieldConfig(field);
          return names.has(field.name) && !config.hidden;
        });
      },
      queryFields() {
        const fields = new Map();
        [...this.searchableFields, ...this.listFilterFields].forEach((field) => {
          fields.set(field.name, field);
        });
        return [...fields.values()];
      },
      visibleQueryFields() {
        return this.isQueryExpanded ? this.queryFields : this.queryFields.slice(0, 3);
      },
      hiddenQueryFieldCount() {
        return Math.max(this.queryFields.length - this.visibleQueryFields.length, 0);
      },
      editableFields() {
        return this.currentFields.filter((field) => {
          const config = this.fieldConfig(field);
          return !field.readonly && !config.hidden && !config.form_hidden;
        });
      },
      detailFields() {
        return this.currentFields.filter((field) => {
          const config = this.fieldConfig(field);
          return !config.hidden && !config.detail_hidden;
        });
      },
      tableColumns() {
        const orderingFields = new Set(this.currentModel?.ordering_fields || []);
        const editableFields = new Set(this.currentModel?.list_editable || []);
        const names = this.currentModel?.list_display || [];
        return names
          .map((name) => {
            const field = this.currentFields.find((item) => item.name === name);
            return field || { name, label: name, type: "str", config: {} };
          })
          .filter((field) => {
            const config = this.fieldConfig(field);
            return !config.hidden && !config.table_hidden;
          })
          .map((field) => {
            return {
              ...field,
              sortable: orderingFields.has(field.name),
              list_editable: editableFields.has(field.name),
            };
          });
      },
      listEditableColumns() {
        return this.tableColumns.filter((column) => this.isListEditableColumn(column));
      },
      listEditDirtyCount() {
        return Object.values(this.listEditDrafts).reduce((count, draft) => {
          return count + Object.keys(draft.values || {}).length;
        }, 0);
      },
      primaryKey() {
        return this.currentModel?.primary_key || "id";
      },
      modelCount() {
        return this.meta.models.length;
      },
      fieldCount() {
        return this.currentFields.length;
      },
      readonlyFieldCount() {
        return this.currentFields.filter((field) => field.readonly).length;
      },
      queryFieldCount() {
        return this.queryFields.length;
      },
      relationFieldCount() {
        return this.currentFields.filter((field) => {
          const config = this.fieldConfig(field);
          return ["select", "autocomplete"].includes(config.widget)
            && Boolean(config.resource);
        }).length;
      },
      resourceInfoRows() {
        return [
          { label: "资源标识", value: this.currentModel?.resource || "-" },
          { label: "分组", value: this.currentModel?.group || "-" },
          { label: "主键", value: this.primaryKey },
          { label: "查询字段", value: this.listText(this.currentModel?.search_fields || []) },
          { label: "筛选字段", value: this.listText(this.currentModel?.list_filter || []) },
          { label: "排序字段", value: this.listText(this.currentModel?.ordering_fields || []) },
          { label: "列表列", value: this.listText(this.currentModel?.list_display || []) },
          { label: "列表编辑", value: this.listText(this.currentModel?.list_editable || []) },
          {
            label: "可用动作",
            value: this.listText(
              (this.currentModel?.allowed_actions || []).map((action) => this.actionLabel(action))
            ),
          },
        ];
      },
      formRules() {
        return this.editableFields.reduce((rules, field) => {
          const fieldRules = this.fieldRules(field);
          if (fieldRules.length) rules[field.name] = fieldRules;
          return rules;
        }, {});
      },
      editableFieldSections() {
        return this.buildFieldSections(this.editableFields);
      },
      detailFieldSections() {
        return this.buildFieldSections(this.detailFields);
      },
      sidebarWidth() {
        return this.isSidebarCollapsed ? "64px" : "224px";
      },
      canExportRows() {
        return (this.currentModel?.allowed_actions || []).includes("list");
      },
      bulkActions() {
        return (this.currentModel?.actions || []).filter((action) => {
          return action.scope === "bulk" || action.scope === "both";
        });
      },
      rowActions() {
        return (this.currentModel?.actions || []).filter((action) => {
          return action.scope === "row" || action.scope === "both";
        });
      },
    },
    async mounted() {
      await this.loadMeta();
    },
    methods: {
      async loadMeta() {
        try {
          this.meta = await api.loadMeta();
          this.title = this.meta.title || this.title;
          document.title = this.title;
          if (this.meta.models.length) {
            await this.selectModel(this.meta.models[0].resource);
          }
        } catch (error) {
          this.notifyError(error.message || "加载后台配置失败");
        }
      },
      async selectModel(resource) {
        if (!this.meta.models.some((model) => model.resource === resource)) return;
        this.ensureResourceTab(resource);
        this.currentResource = resource;
        this.selectedRow = null;
        this.selectedRows = [];
        this.listEditDrafts = {};
        this.pagination.page = 1;
        this.ordering = "";
        this.isQueryExpanded = false;
        this.resetFilters(false);
        await this.loadSelectOptions();
        await this.queryRows();
      },
      ensureResourceTab(resource) {
        if (!this.openedResources.includes(resource)) {
          this.openedResources.push(resource);
        }
      },
      async switchResourceTab(resource) {
        if (resource === this.currentResource) return;
        await this.selectModel(resource);
      },
      async closeResourceTab(resource, event) {
        event?.stopPropagation?.();
        const index = this.openedResources.indexOf(resource);
        if (index === -1 || this.openedResources.length <= 1) return;

        const wasActive = resource === this.currentResource;
        this.openedResources.splice(index, 1);
        if (!wasActive) return;

        const nextResource = this.openedResources[index] || this.openedResources[index - 1];
        if (nextResource) await this.selectModel(nextResource);
      },
      async queryRows(options = {}) {
        if (!this.currentModel) return;
        this.loading = true;
        try {
          const params = this.listParams();
          const data = await api.listRows(this.currentModel.resource, params);
          this.rows = data.results || [];
          this.total = data.count || 0;
          this.listEditDrafts = {};
          if (options.notify) {
            this.notifySuccess(options.message || "查询成功");
          }
        } catch (error) {
          this.notifyError(error.message || "查询失败");
        } finally {
          this.loading = false;
        }
      },
      submitQuery(options = {}) {
        this.pagination.page = 1;
        this.queryRows({ notify: true, ...options });
      },
      resetFilters(shouldQuery = true) {
        this.pagination.page = 1;
        this.filters = this.emptyFilterState();
        if (shouldQuery) this.queryRows({ notify: true, message: "重置成功" });
      },
      listParams(options = {}) {
        const includePagination = options.includePagination !== false;
        const params = this.queryParams();
        if (this.globalKeyword && this.currentModel.search_fields.length) {
          params.search = this.globalKeyword;
        }
        if (this.ordering) {
          params.ordering = this.ordering;
        }
        if (includePagination) {
          params.limit = this.pagination.pageSize;
          params.offset = (this.pagination.page - 1) * this.pagination.pageSize;
        }
        return params;
      },
      async exportRows() {
        if (!this.currentModel) return;
        this.exporting = true;
        try {
          const result = await api.exportCsv(
            this.currentModel.resource,
            this.listParams({ includePagination: false })
          );
          this.downloadBlob(
            result.blob,
            result.filename || `${this.currentModel.resource}.csv`
          );
          this.notifySuccess("导出成功");
        } catch (error) {
          this.notifyError(error.message || "导出失败");
        } finally {
          this.exporting = false;
        }
      },
      downloadBlob(blob, filename) {
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.setTimeout(() => URL.revokeObjectURL(url), 0);
      },
      rowKey(row) {
        const value = row?.[this.primaryKey];
        return value === null || value === undefined ? "" : String(value);
      },
      isListEditableColumn(column) {
        const config = this.fieldConfig(column);
        return Boolean(column.list_editable)
          && !column.readonly
          && !column.computed
          && !config.hidden
          && !config.table_hidden
          && (this.currentModel?.allowed_actions || []).includes("update");
      },
      listEditValue(row, column) {
        const key = this.rowKey(row);
        const draft = this.listEditDrafts[key];
        if (draft?.values && Object.prototype.hasOwnProperty.call(draft.values, column.name)) {
          return draft.values[column.name];
        }
        return utils.formatDateValue(row[column.name], this.fieldWidget(column));
      },
      setListEditValue(row, column, value) {
        const key = this.rowKey(row);
        if (!key) return;

        const drafts = { ...this.listEditDrafts };
        const draft = drafts[key]
          ? { ...drafts[key], values: { ...drafts[key].values } }
          : { pk: row[this.primaryKey], values: {} };
        const original = utils.formatDateValue(row[column.name], this.fieldWidget(column));

        if (this.normalizedValue(value) === this.normalizedValue(original)) {
          delete draft.values[column.name];
        } else {
          draft.values[column.name] = value;
        }

        if (Object.keys(draft.values).length) {
          drafts[key] = draft;
        } else {
          delete drafts[key];
        }
        this.listEditDrafts = drafts;
      },
      normalizedValue(value) {
        if (value === null || value === undefined) return "";
        if (Array.isArray(value) || typeof value === "object") {
          return JSON.stringify(value);
        }
        return String(value);
      },
      isListCellDirty(row, column) {
        const draft = this.listEditDrafts[this.rowKey(row)];
        return Boolean(
          draft?.values
          && Object.prototype.hasOwnProperty.call(draft.values, column.name)
        );
      },
      listEditPayloads() {
        return Object.values(this.listEditDrafts).filter((draft) => {
          return draft.pk !== null
            && draft.pk !== undefined
            && Object.keys(draft.values || {}).length;
        });
      },
      resetListEdits() {
        this.listEditDrafts = {};
      },
      async saveListEdits() {
        const payloads = this.listEditPayloads();
        if (!payloads.length || !this.currentModel) return;

        this.listEditSaving = true;
        try {
          for (const draft of payloads) {
            await api.updateRow(this.currentModel.resource, draft.pk, draft.values);
          }
          this.notifySuccess(`已保存 ${payloads.length} 行修改`);
          await this.queryRows();
        } catch (error) {
          this.notifyError(error.message || "保存本页修改失败");
        } finally {
          this.listEditSaving = false;
        }
      },
      onSelectionChange(selection) {
        this.selectedRows = selection;
        this.selectedRow = selection[0] || null;
      },
      openCreate() {
        this.editingRow = null;
        this.drawerMode = "create";
        this.drawerTitle = `增加 ${this.currentModel.label}`;
        this.formData = utils.emptyFormData(this.editableFields);
        this.loadSelectOptions(this.editableFields);
        this.drawerVisible = true;
      },
      openSelectedEdit() {
        if (this.selectedRow) this.openEdit(this.selectedRow);
      },
      async openView(row) {
        this.editingRow = null;
        this.drawerMode = "view";
        this.drawerTitle = `查看 ${this.currentModel.label}`;
        this.detailData = row;
        this.drawerVisible = true;
        await this.loadSelectOptions(this.detailFields);
        try {
          this.detailData = await api.retrieveRow(
            this.currentModel.resource,
            row[this.primaryKey]
          );
        } catch (error) {
          this.notifyError(error.message || "加载详情失败");
        }
      },
      openEdit(row) {
        this.editingRow = row;
        this.drawerMode = "edit";
        this.drawerTitle = `修改 ${this.currentModel.label}`;
        this.formData = utils.rowToFormData(this.editableFields, row);
        this.loadSelectOptions(this.editableFields);
        this.drawerVisible = true;
      },
      async saveRow() {
        this.saving = true;
        try {
          await this.validateForm();
          const payload = this.formPayload();
          if (this.editingRow) {
            await api.updateRow(
              this.currentModel.resource,
              this.editingRow[this.primaryKey],
              payload
            );
            this.notifySuccess("修改成功");
          } else {
            await api.createRow(this.currentModel.resource, payload);
            this.notifySuccess("新增成功");
          }
          this.drawerVisible = false;
          await this.queryRows();
        } catch (error) {
          this.notifyError(error.message || "保存失败");
        } finally {
          this.saving = false;
        }
      },
      formPayload() {
        const payload = { ...this.formData };
        this.editableFields.forEach((field) => {
          if (this.fieldWidget(field) !== "json") return;
          const value = payload[field.name];
          if (value === "" || value === null || value === undefined) {
            payload[field.name] = null;
            return;
          }
          try {
            payload[field.name] = typeof value === "string"
              ? JSON.parse(value)
              : value;
          } catch {
            throw new Error(`${field.label} 不是合法 JSON`);
          }
        });
        return payload;
      },
      async deleteSelected() {
        if (!this.selectedRows.length) return;
        if (this.selectedRows.length === 1) {
          await this.deleteRow(this.selectedRows[0]);
          return;
        }
        await this.deleteSelectedRows();
      },
      async deleteSelectedRows() {
        if (!this.selectedRows.length) return;
        await ElementPlus.ElMessageBox.confirm(
          `确认删除选中的 ${this.selectedRows.length} 条记录？`,
          "批量删除确认",
          {
            type: "warning",
            confirmButtonText: "删除",
            cancelButtonText: "取消",
          }
        );
        let successCount = 0;
        let failedCount = 0;
        this.loading = true;
        try {
          for (const row of this.selectedRows) {
            try {
              await api.deleteRow(this.currentModel.resource, row[this.primaryKey]);
              successCount += 1;
            } catch {
              failedCount += 1;
            }
          }
          await this.queryRows();
          this.selectedRows = [];
          this.selectedRow = null;
          if (failedCount) {
            this.notifyError(`已删除 ${successCount} 条，失败 ${failedCount} 条`);
          } else {
            this.notifySuccess(`批量删除成功，共 ${successCount} 条`);
          }
        } finally {
          this.loading = false;
        }
      },
      async deleteRow(row) {
        await ElementPlus.ElMessageBox.confirm("确认删除这条记录？", "删除确认", {
          type: "warning",
          confirmButtonText: "删除",
          cancelButtonText: "取消",
        });
        try {
          await api.deleteRow(this.currentModel.resource, row[this.primaryKey]);
          await this.queryRows();
          this.notifySuccess("删除成功");
        } catch (error) {
          this.notifyError(error.message || "删除失败");
        }
      },
      notifySuccess(message) {
        ElementPlus.ElMessage.success({
          message,
          showClose: true,
          duration: 1800,
        });
      },
      notifyError(message) {
        ElementPlus.ElMessage.error({
          message,
          showClose: true,
          duration: 2600,
        });
      },
      toggleSidebar() {
        this.isSidebarCollapsed = !this.isSidebarCollapsed;
      },
      toggleResourcePanel() {
        this.isResourcePanelCollapsed = !this.isResourcePanelCollapsed;
      },
      toggleQueryFields() {
        this.isQueryExpanded = !this.isQueryExpanded;
      },
      handlePageChange(page) {
        this.pagination.page = page;
        this.queryRows();
      },
      handlePageSizeChange(pageSize) {
        this.pagination.pageSize = pageSize;
        this.pagination.page = 1;
        this.queryRows();
      },
      handleSortChange({ prop, order }) {
        if (!prop || !order) {
          this.ordering = "";
        } else {
          this.ordering = order === "descending" ? `-${prop}` : prop;
        }
        this.pagination.page = 1;
        this.queryRows({ notify: true, message: "排序成功" });
      },
      fieldConfig(field) {
        return utils.fieldConfig(field);
      },
      fieldWidget(field) {
        return utils.fieldWidget(field);
      },
      filterWidget(field) {
        const widget = this.fieldConfig(field).widget;
        if (this.isRangeFilterField(field)) {
          return this.fieldWidget(field) === "date" ? "date_range" : "datetime_range";
        }
        if (this.hasChoices(field)) return "select";
        if (widget === "autocomplete") return "autocomplete";
        if (widget === "select") return "select";
        if (field.type === "bool") return "bool";
        return "input";
      },
      fieldPlaceholder(field) {
        return this.fieldConfig(field).placeholder || field.label;
      },
      fieldHelpText(field) {
        return this.fieldConfig(field).help_text || "";
      },
      tableColumnWidth(field) {
        return this.fieldConfig(field).width || undefined;
      },
      actionLabel(name) {
        const labels = {
          list: "列表",
          retrieve: "查看",
          create: "新增",
          update: "修改",
          destroy: "删除",
        };
        return labels[name] || name;
      },
      listText(values) {
        return values && values.length ? values.join("、") : "-";
      },
      fieldBadges(field) {
        const config = this.fieldConfig(field);
        const badges = [];
        if (field.primary_key) badges.push({ label: "主键", type: "primary" });
        if (field.computed) badges.push({ label: "计算列", type: "success" });
        if ((this.currentModel?.list_editable || []).includes(field.name)) {
          badges.push({ label: "列表编辑", type: "warning" });
        }
        if (field.readonly) badges.push({ label: "只读", type: "info" });
        if (field.nullable) badges.push({ label: "可空", type: "info" });
        if (config.hidden) badges.push({ label: "隐藏", type: "danger" });
        if (config.table_hidden) badges.push({ label: "表格隐藏", type: "warning" });
        if (config.form_hidden) badges.push({ label: "表单隐藏", type: "warning" });
        if (config.detail_hidden) badges.push({ label: "详情隐藏", type: "warning" });
        return badges;
      },
      fieldRules(field) {
        const config = this.fieldConfig(field);
        if (Array.isArray(config.rules)) return config.rules;
        if (field.nullable || field.default || field.type === "bool") return [];
        const trigger = ["select", "date", "datetime"].includes(this.fieldWidget(field))
          ? "change"
          : "blur";
        return [
          {
            required: true,
            message: `请输入${field.label}`,
            trigger,
          },
        ];
      },
      datePickerType(field) {
        return this.fieldWidget(field) === "date" ? "date" : "datetime";
      },
      dateValueFormat(field) {
        return this.fieldWidget(field) === "date" ? "YYYY-MM-DD" : "YYYY-MM-DDTHH:mm:ss";
      },
      rangePickerType(field) {
        return this.filterWidget(field) === "date_range" ? "daterange" : "datetimerange";
      },
      rangeValueFormat(field) {
        return this.filterWidget(field) === "date_range"
          ? "YYYY-MM-DD"
          : "YYYY-MM-DDTHH:mm:ss";
      },
      isListFilterField(field) {
        return (this.currentModel?.list_filter || []).includes(field.name);
      },
      isRangeFilterField(field) {
        return this.isListFilterField(field) && (
          this.fieldWidget(field) === "date" || this.fieldWidget(field) === "datetime"
        );
      },
      emptyFilterState() {
        return this.queryFields.reduce((filters, field) => {
          const widget = this.filterWidget(field);
          filters[field.name] = ["date_range", "datetime_range"].includes(widget)
            ? []
            : "";
          return filters;
        }, {});
      },
      queryParams() {
        return this.queryFields.reduce((params, field) => {
          const value = this.filters[field.name];
          const widget = this.filterWidget(field);
          if (["date_range", "datetime_range"].includes(widget)) {
            if (Array.isArray(value)) {
              if (value[0]) params[`${field.name}__gte`] = value[0];
              if (value[1]) params[`${field.name}__lte`] = value[1];
            }
            return params;
          }
          if (value !== "" && value !== null && value !== undefined) {
            params[field.name] = value;
          }
          return params;
        }, {});
      },
      async validateForm() {
        if (!this.$refs.editForm) return;
        await this.$refs.editForm.validate();
      },
      buildFieldSections(fields) {
        if (!fields.length) return [];
        const configured = this.currentModel?.fieldsets || [];
        if (!configured.length) {
          return [{ title: "", description: "", fields }];
        }

        const fieldMap = new Map(fields.map((field) => [field.name, field]));
        const used = new Set();
        const sections = configured
          .map((fieldset) => {
            const sectionFields = (fieldset.fields || [])
              .map((name) => fieldMap.get(name))
              .filter((field) => {
                if (!field || used.has(field.name)) return false;
                used.add(field.name);
                return true;
              });
            return { ...fieldset, fields: sectionFields };
          })
          .filter((section) => section.fields.length);

        const remaining = fields.filter((field) => !used.has(field.name));
        if (remaining.length) {
          sections.push({
            title: configured.length ? "其他" : "",
            description: "",
            fields: remaining,
          });
        }
        return sections;
      },
      optionKey(field) {
        const config = this.fieldConfig(field);
        return `${this.currentResource}:${field.name}:${config.resource || ""}`;
      },
      optionValueField(field) {
        const config = this.fieldConfig(field);
        if (config.value_field) return config.value_field;
        const model = this.meta.models.find((item) => item.resource === config.resource);
        return model?.primary_key || "id";
      },
      optionLabelField(field) {
        return this.fieldConfig(field).label_field || "name";
      },
      optionLabel(row, field) {
        const valueField = this.optionValueField(field);
        const labelField = this.optionLabelField(field);
        return row[labelField] ?? row.name ?? row.title ?? row[valueField];
      },
      selectOptions(field) {
        if (this.hasChoices(field)) return utils.fieldChoices(field);
        return this.relationOptions[this.optionKey(field)] || [];
      },
      async loadSelectOptions(fields = this.currentFields) {
        const selectFields = fields.filter((field) => {
          const config = this.fieldConfig(field);
          return ["select", "autocomplete"].includes(config.widget)
            && config.resource
            && !this.hasChoices(field);
        });
        await Promise.all(
          selectFields.map(async (field) => {
            const key = this.optionKey(field);
            if (this.relationOptions[key]) return;
            await this.searchRemoteOptions(field, "");
          })
        );
      },
      isOptionLoading(field) {
        return Boolean(this.relationLoading[this.optionKey(field)]);
      },
      async searchRemoteOptions(field, keyword = "") {
        const config = this.fieldConfig(field);
        if (!config.resource || this.hasChoices(field)) return;
        const key = this.optionKey(field);
        this.relationLoading[key] = true;
        try {
          const params = {
            limit: config.limit || 100,
            offset: 0,
          };
          if (keyword) params.search = keyword;
          const data = await api.listOptions(config.resource, params);
          const valueField = this.optionValueField(field);
          this.relationOptions[key] = (data.results || []).map((row) => ({
            label: this.optionLabel(row, field),
            value: row[valueField],
          }));
        } catch (error) {
          this.notifyError(error.message || `加载 ${field.label} 选项失败`);
        } finally {
          this.relationLoading[key] = false;
        }
      },
      formatTableCell(row, field) {
        if (this.hasChoices(field)) {
          return this.choiceByValue(field, row[field.name])?.label ?? this.formatCell(row[field.name]);
        }
        if (this.fieldWidget(field) === "select") {
          const option = this.selectOptions(field).find(
            (item) => item.value === row[field.name]
          );
          return option?.label ?? this.formatCell(row[field.name]);
        }
        if (field.type === "bool") {
          if (row[field.name] === null || row[field.name] === undefined) return "";
          return row[field.name] ? "是" : "否";
        }
        return this.formatCell(row[field.name]);
      },
      formatDetailCell(field) {
        return this.formatTableCell(this.detailData, field) || "-";
      },
      hasChoices: utils.hasChoices,
      choiceByValue: utils.choiceByValue,
      choiceTagType(value, field) {
        const choice = this.choiceByValue(field, value);
        return choice?.type || choice?.tag_type || "info";
      },
      actionType(action) {
        return action.variant || "primary";
      },
      async confirmAdminAction(action, fallbackMessage) {
        if (!action.confirmation) return;
        await ElementPlus.ElMessageBox.confirm(
          action.confirmation || fallbackMessage,
          "操作确认",
          {
            type: "warning",
            confirmButtonText: "确认",
            cancelButtonText: "取消",
          }
        );
      },
      async runBulkAction(actionName) {
        const action = this.bulkActions.find((item) => item.name === actionName);
        if (!action || !this.selectedRows.length) return;
        try {
          await this.confirmAdminAction(action, `确认执行 ${action.label}？`);
          this.loading = true;
          const pks = this.selectedRows.map((row) => row[this.primaryKey]);
          const result = await api.runBulkAction(
            this.currentModel.resource,
            action.name,
            pks
          );
          this.notifySuccess(result?.message || `${action.label}成功`);
          this.selectedRows = [];
          this.selectedRow = null;
          await this.queryRows();
        } catch (error) {
          if (error === "cancel" || error === "close") return;
          this.notifyError(error.message || `${action.label}失败`);
        } finally {
          this.loading = false;
        }
      },
      async runRowAction(action, row) {
        try {
          await this.confirmAdminAction(action, `确认执行 ${action.label}？`);
          this.loading = true;
          const result = await api.runRowAction(
            this.currentModel.resource,
            row[this.primaryKey],
            action.name
          );
          this.notifySuccess(result?.message || `${action.label}成功`);
          await this.queryRows();
        } catch (error) {
          if (error === "cancel" || error === "close") return;
          this.notifyError(error.message || `${action.label}失败`);
        } finally {
          this.loading = false;
        }
      },
      formatCell: utils.formatCell,
      isNumberField: utils.isNumberField,
    },
  }).use(ElementPlus).mount("#app");
})();

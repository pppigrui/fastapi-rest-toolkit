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
        loading: false,
        saving: false,
      };
    },
    computed: {
      currentModel() {
        return this.meta.models.find((model) => model.resource === this.currentResource);
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
            return { ...field, sortable: orderingFields.has(field.name) };
          });
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
      formRules() {
        return this.editableFields.reduce((rules, field) => {
          const fieldRules = this.fieldRules(field);
          if (fieldRules.length) rules[field.name] = fieldRules;
          return rules;
        }, {});
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
        this.currentResource = resource;
        this.selectedRow = null;
        this.selectedRows = [];
        this.pagination.page = 1;
        this.ordering = "";
        this.resetFilters(false);
        await this.loadSelectOptions();
        await this.queryRows();
      },
      async queryRows(options = {}) {
        if (!this.currentModel) return;
        this.loading = true;
        try {
          const params = { ...this.filters };
          if (this.globalKeyword && this.currentModel.search_fields.length) {
            params.search = this.globalKeyword;
          }
          if (this.ordering) {
            params.ordering = this.ordering;
          }
          params.limit = this.pagination.pageSize;
          params.offset = (this.pagination.page - 1) * this.pagination.pageSize;
          const data = await api.listRows(this.currentModel.resource, params);
          this.rows = data.results || [];
          this.total = data.count || 0;
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
        this.filters = utils.searchableFilterState(this.queryFields);
        if (shouldQuery) this.queryRows({ notify: true, message: "重置成功" });
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
      openSelectedView() {
        if (this.selectedRow) this.openView(this.selectedRow);
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
          if (this.editingRow) {
            await api.updateRow(
              this.currentModel.resource,
              this.editingRow[this.primaryKey],
              this.formData
            );
            this.notifySuccess("修改成功");
          } else {
            await api.createRow(this.currentModel.resource, this.formData);
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
      deleteSelected() {
        if (this.selectedRow) this.deleteRow(this.selectedRow);
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
      async validateForm() {
        if (!this.$refs.editForm) return;
        await this.$refs.editForm.validate();
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
        return this.relationOptions[this.optionKey(field)] || [];
      },
      async loadSelectOptions(fields = this.currentFields) {
        const selectFields = fields.filter((field) => {
          const config = this.fieldConfig(field);
          return config.widget === "select" && config.resource;
        });
        await Promise.all(
          selectFields.map(async (field) => {
            const key = this.optionKey(field);
            if (this.relationOptions[key]) return;
            const config = this.fieldConfig(field);
            try {
              const data = await api.listRows(config.resource, {
                limit: config.limit || 100,
                offset: 0,
              });
              const valueField = this.optionValueField(field);
              this.relationOptions[key] = (data.results || []).map((row) => ({
                label: this.optionLabel(row, field),
                value: row[valueField],
              }));
            } catch (error) {
              this.notifyError(error.message || `加载 ${field.label} 选项失败`);
            }
          })
        );
      },
      formatTableCell(row, field) {
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
      formatCell: utils.formatCell,
      isNumberField: utils.isNumberField,
    },
  }).use(ElementPlus).mount("#app");
})();

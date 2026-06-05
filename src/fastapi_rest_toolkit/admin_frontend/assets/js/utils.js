(function () {
  function formatCell(value) {
    if (value === null || value === undefined) return "";
    return String(value);
  }

  function isNumberField(field) {
    return field.type === "int" || field.type === "float";
  }

  function isDateField(field) {
    return field.type === "date";
  }

  function isDateTimeField(field) {
    return field.type === "datetime";
  }

  function fieldConfig(field) {
    return field.config || {};
  }

  function fieldWidget(field) {
    const widget = fieldConfig(field).widget;
    if (widget) return widget;
    if (field.type === "bool") return "switch";
    if (isNumberField(field)) return "number";
    if (isDateTimeField(field)) return "datetime";
    if (isDateField(field)) return "date";
    return "input";
  }

  function formatDateValue(value, widget) {
    if (!value) return value;
    const text = String(value);
    if (widget === "date") return text.slice(0, 10);
    if (widget === "datetime") return text.slice(0, 19).replace(" ", "T");
    return value;
  }

  function emptyFormData(fields) {
    return fields.reduce((data, field) => {
      data[field.name] = field.type === "bool" || fieldConfig(field).widget === "switch" ? false : null;
      return data;
    }, {});
  }

  function rowToFormData(fields, row) {
    return fields.reduce((data, field) => {
      data[field.name] = formatDateValue(row[field.name], fieldWidget(field));
      return data;
    }, {});
  }

  function searchableFilterState(fields) {
    return fields.reduce((filters, field) => {
      filters[field.name] = "";
      return filters;
    }, {});
  }

  window.AdminUtils = {
    emptyFormData,
    fieldConfig,
    fieldWidget,
    formatCell,
    formatDateValue,
    isDateField,
    isDateTimeField,
    isNumberField,
    rowToFormData,
    searchableFilterState,
  };
})();

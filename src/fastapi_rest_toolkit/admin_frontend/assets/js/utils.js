(function () {
  function formatCell(value) {
    if (value === null || value === undefined) return "";
    if (Array.isArray(value) || typeof value === "object") {
      return JSON.stringify(value);
    }
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

  function fieldChoices(field) {
    return Array.isArray(field.choices) ? field.choices : [];
  }

  function hasChoices(field) {
    return fieldChoices(field).length > 0;
  }

  function choiceByValue(field, value) {
    return fieldChoices(field).find((choice) => {
      return choice.value === value || String(choice.value) === String(value);
    });
  }

  function fieldWidget(field) {
    const widget = fieldConfig(field).widget;
    if (widget) return widget;
    if (hasChoices(field)) return "select";
    if (field.type === "bool") return "switch";
    if (isNumberField(field)) return "number";
    if (isDateTimeField(field)) return "datetime";
    if (isDateField(field)) return "date";
    if (field.type === "dict" || field.type === "list") return "json";
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
      const widget = fieldWidget(field);
      if (widget === "json") {
        data[field.name] = field.type === "list" ? "[]" : "{}";
        return data;
      }
      data[field.name] = field.type === "bool" || widget === "switch" ? false : null;
      return data;
    }, {});
  }

  function rowToFormData(fields, row) {
    return fields.reduce((data, field) => {
      const widget = fieldWidget(field);
      if (widget === "json") {
        const value = row[field.name];
        data[field.name] = value === null || value === undefined
          ? ""
          : JSON.stringify(value, null, 2);
        return data;
      }
      data[field.name] = formatDateValue(row[field.name], widget);
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
    choiceByValue,
    emptyFormData,
    fieldChoices,
    fieldConfig,
    fieldWidget,
    formatCell,
    formatDateValue,
    isDateField,
    isDateTimeField,
    isNumberField,
    hasChoices,
    rowToFormData,
    searchableFilterState,
  };
})();

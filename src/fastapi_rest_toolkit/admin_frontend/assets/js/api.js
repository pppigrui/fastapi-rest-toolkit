(function () {
  function apiBase() {
    const base = window.__FASTAPI_REST_ADMIN_BASE__ || window.location.pathname;
    return base.replace(/\/$/, "") + "/api";
  }

  async function request(path, options = {}) {
    const response = await fetch(apiBase() + path, options);
    if (!response.ok) {
      const message = await response.text();
      throw new Error(parseErrorMessage(message, response.status));
    }
    if (response.status === 204) return null;
    return response.json();
  }

  function parseErrorMessage(message, status) {
    if (!message) return `请求失败：${status}`;
    try {
      const data = JSON.parse(message);
      if (typeof data.detail === "string") return data.detail;
      if (Array.isArray(data.detail)) return data.detail.map((item) => item.msg).join("; ");
      return JSON.stringify(data.detail || data);
    } catch {
      return message;
    }
  }

  function requestUrl(path, params = {}) {
    return apiBase() + path + toQueryString(params);
  }

  async function requestBlob(path, params = {}) {
    const response = await fetch(requestUrl(path, params));
    if (!response.ok) {
      const message = await response.text();
      throw new Error(parseErrorMessage(message, response.status));
    }
    return {
      blob: await response.blob(),
      filename: responseFilename(response.headers.get("Content-Disposition")),
    };
  }

  function responseFilename(disposition) {
    if (!disposition) return "";
    const match = disposition.match(/filename="?([^"]+)"?/i);
    return match ? match[1] : "";
  }

  function toQueryString(params) {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== "" && value !== null && value !== undefined) {
        query.set(key, value);
      }
    });
    const text = query.toString();
    return text ? `?${text}` : "";
  }

  window.AdminApi = {
    loadMeta() {
      return request("/meta");
    },
    listRows(resource, params) {
      return request(`/${resource}${toQueryString(params)}`);
    },
    listOptions(resource, params) {
      return request(`/${resource}${toQueryString(params)}`);
    },
    exportCsv(resource, params) {
      return requestBlob(`/${resource}/export.csv`, params);
    },
    retrieveRow(resource, pk) {
      return request(`/${resource}/${pk}`);
    },
    createRow(resource, payload) {
      return request(`/${resource}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    },
    updateRow(resource, pk, payload) {
      return request(`/${resource}/${pk}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    },
    deleteRow(resource, pk) {
      return request(`/${resource}/${pk}`, { method: "DELETE" });
    },
    runBulkAction(resource, action, pks) {
      return request(`/${resource}/actions/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pks }),
      });
    },
    runRowAction(resource, pk, action) {
      return request(`/${resource}/${pk}/actions/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
    },
  };
})();

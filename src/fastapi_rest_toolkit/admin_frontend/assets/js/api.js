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
  };
})();

const BASE = "/api/customers";

async function request(url, options = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    // Surface DRF field errors as a readable string
    const detail =
      data.detail ||
      data.non_field_errors?.[0] ||
      Object.entries(data)
        .map(([k, v]) => `${k}: ${Array.isArray(v) ? v[0] : v}`)
        .join(" · ") ||
      `HTTP ${res.status}`;
    throw new Error(detail);
  }

  return data;
}

function authRequest(url, options = {}, token = null) {
  const headers = { "Content-Type": "application/json", ...options.headers };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return request(url, { ...options, headers });
}

export const profileApi = {
  get: (token) => authRequest(`${BASE}/profile/`, {}, token),
  update: (data, token) =>
    authRequest(`${BASE}/profile/`, {
      method: "PUT",
      body: JSON.stringify(data),
    }, token),
};

export const authApi = {
  login: (email, password) =>
    request(`${BASE}/login/`, {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  loginManager: (email, password) =>
    request("/api/managers/login/", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  loginStaff: (email, password) =>
    request("/api/staff/login/", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  register: ({ email, password, password_confirm, first_name, last_name, phone, address }) =>
    request(`${BASE}/register/`, {
      method: "POST",
      body: JSON.stringify({ email, password, password_confirm, first_name, last_name, phone, address }),
    }),
};

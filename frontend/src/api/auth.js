const BASE_AUTH = "/api/auth";
const BASE_USERS = "/api/users";

async function request(url, options = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
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
  get: (token) => authRequest(`${BASE_USERS}/profile/`, {}, token),
  update: (data, token) =>
    authRequest(`${BASE_USERS}/profile/`, {
      method: "PUT",
      body: JSON.stringify(data),
    }, token),
};

export const authApi = {
  login: (email, password) =>
    request(`${BASE_AUTH}/login/`, {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  register: ({ email, password, password_confirm, first_name, last_name, phone, address }) =>
    request(`${BASE_AUTH}/register/`, {
      method: "POST",
      body: JSON.stringify({ email, password, password_confirm, first_name, last_name, phone, address }),
    }),
};

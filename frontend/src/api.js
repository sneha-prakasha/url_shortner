// Tiny fetch wrapper: adds the login token and turns errors into readable messages.
const BASE = "/api";
const KEY = "snip_token";

export const tokenStore = {
  get() {
    try { return localStorage.getItem(KEY); } catch { return null; }
  },
  set(token) {
    try { localStorage.setItem(KEY, token); } catch { /* storage blocked */ }
  },
  clear() {
    try { localStorage.removeItem(KEY); } catch { /* storage blocked */ }
  },
};

function readableError(data, status) {
  const detail = data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    // FastAPI validation errors look like [{loc, msg}, ...]
    return detail.map((d) => String(d.msg).replace(/^Value error, /, "")).join(". ");
  }
  return `Something went wrong (${status})`;
}

export async function api(path, { method = "GET", body } = {}) {
  const headers = {};
  const token = tokenStore.get();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  let res;
  try {
    res = await fetch(BASE + path, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new Error("Can't reach the server. Check your connection.");
  }

  if (res.status === 204) return null;
  const data = await res.json().catch(() => null);

  if (!res.ok) {
    const err = new Error(readableError(data, res.status));
    err.status = res.status;
    throw err;
  }
  return data;
}

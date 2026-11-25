export const stripProtocol = (url) => url.replace(/^https?:\/\//, "");

export const fmtNumber = (n) => new Intl.NumberFormat().format(n ?? 0);

export const fmtDate = (iso) =>
  iso
    ? new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })
    : "";

export const fmtDateTime = (iso) =>
  iso
    ? new Date(iso).toLocaleString(undefined, {
        day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
      })
    : "";

// "2026-11-22" -> "Nov 22"
export const fmtDay = (isoDay) =>
  new Date(isoDay + "T00:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" });

// ISO (UTC) -> value for <input type="datetime-local"> in the user's own timezone
export function toLocalInput(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
}

// value from <input type="datetime-local"> -> ISO string in UTC (or null if empty)
export const fromLocalInput = (value) => (value ? new Date(value).toISOString() : null);

export function statusOf(link) {
  if (!link.is_active) return { label: "Paused", tone: "muted" };
  if (link.is_expired) return { label: "Expired", tone: "danger" };
  return { label: "Active", tone: "ok" };
}

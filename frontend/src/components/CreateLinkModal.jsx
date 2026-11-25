import { useEffect, useState } from "react";
import { api } from "../api";
import { fromLocalInput } from "../format";
import { Icon } from "./Icon";

export default function CreateLinkModal({ onClose, onCreated }) {
  const [form, setForm] = useState({ url: "", alias: "", label: "", expires: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const link = await api("/links", {
        method: "POST",
        body: {
          url: form.url.trim(),
          alias: form.alias.trim() || null,
          label: form.label.trim() || null,
          expires_at: fromLocalInput(form.expires),
        },
      });
      onCreated(link);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <form className="modal" onSubmit={submit} onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h2>New short link</h2>
          <button type="button" className="btn ghost icon-only" onClick={onClose} aria-label="Close">
            <Icon name="x" />
          </button>
        </div>

        <label className="field">
          <span>Long URL</span>
          <input
            type="url"
            required
            autoFocus
            placeholder="https://example.com/a/very/long/page"
            value={form.url}
            onChange={set("url")}
          />
        </label>

        <div className="row">
          <label className="field">
            <span>Custom alias <em>(optional)</em></span>
            <input
              placeholder="my-resume"
              pattern="[A-Za-z0-9_\-]{3,32}"
              title="3-32 characters: letters, numbers, - or _"
              value={form.alias}
              onChange={set("alias")}
            />
            <small className="muted mono">{window.location.origin}/{form.alias || "…"}</small>
          </label>
          <label className="field">
            <span>Label <em>(optional)</em></span>
            <input maxLength={100} placeholder="LinkedIn" value={form.label} onChange={set("label")} />
          </label>
        </div>

        <label className="field">
          <span>Expires at <em>(optional)</em></span>
          <input type="datetime-local" value={form.expires} onChange={set("expires")} />
        </label>

        {error && <p className="error">{error}</p>}

        <div className="modal-actions">
          <button type="button" className="btn ghost" onClick={onClose}>Cancel</button>
          <button className="btn primary" disabled={busy}>
            {busy ? "Creating…" : "Create link"}
          </button>
        </div>
      </form>
    </div>
  );
}

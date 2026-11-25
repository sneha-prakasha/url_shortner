import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import BarList from "../components/BarList";
import ClicksChart from "../components/ClicksChart";
import CopyButton from "../components/CopyButton";
import { Icon } from "../components/Icon";
import QRModal from "../components/QRModal";
import { fmtDateTime, fmtNumber, fromLocalInput, statusOf, toLocalInput } from "../format";

export default function LinkDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState("");
  const [showQr, setShowQr] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [label, setLabel] = useState("");
  const [expires, setExpires] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState("");
  const menuRef = useRef(null);

  function load() {
    api(`/links/${id}`)
      .then((d) => {
        setDetail(d);
        setLabel(d.link.label || "");
        setExpires(toLocalInput(d.link.expires_at));
      })
      .catch((e) => setError(e.message));
  }
  useEffect(load, [id]);

  // close the ⋮ menu when clicking elsewhere
  useEffect(() => {
    const onDoc = (e) => menuRef.current && !menuRef.current.contains(e.target) && setMenuOpen(false);
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  if (error) {
    return (
      <>
        <p className="error">{error}</p>
        <Link to="/links">← Back to links</Link>
      </>
    );
  }
  if (!detail) return <p className="muted">Loading…</p>;

  const { link, stats } = detail;
  const status = statusOf(link);
  const dirty = label !== (link.label || "") || expires !== toLocalInput(link.expires_at);

  async function save() {
    setSaving(true);
    setSaveMsg("");
    try {
      await api(`/links/${link.id}`, {
        method: "PATCH",
        body: { label: label.trim() || null, expires_at: fromLocalInput(expires) },
      });
      setSaveMsg("Saved");
      load();
    } catch (e) {
      setSaveMsg(e.message);
    }
    setSaving(false);
  }

  async function togglePause() {
    setMenuOpen(false);
    try {
      await api(`/links/${link.id}`, { method: "PATCH", body: { is_active: !link.is_active } });
      load();
    } catch (e) {
      setError(e.message);
    }
  }

  async function remove() {
    setMenuOpen(false);
    if (!window.confirm("Delete this link and all its click data? This can't be undone.")) return;
    try {
      await api(`/links/${link.id}`, { method: "DELETE" });
      navigate("/links");
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <>
      <header className="page-head">
        <div className="title-row">
          <Link to="/links" className="back" aria-label="Back to links">
            <Icon name="back" size={22} />
          </Link>
          <h1>Link Details</h1>
        </div>
        <div className="menu-wrap" ref={menuRef}>
          <button className="btn secondary icon-only square" onClick={() => setMenuOpen(!menuOpen)} aria-label="More actions">
            <Icon name="dots" size={20} />
          </button>
          {menuOpen && (
            <div className="menu">
              <button onClick={togglePause}>{link.is_active ? "Pause link" : "Resume link"}</button>
              <button className="danger-text" onClick={remove}>
                <Icon name="trash" size={16} /> Delete link
              </button>
            </div>
          )}
        </div>
      </header>

      {/* top card */}
      <section className="card hero">
        <div className="hero-main">
          <div className="hero-title">
            <h2>{link.label || link.code}</h2>
            <span className={`pill ${status.tone}`}>{status.label}</span>
          </div>
          <a className="hero-url" href={link.long_url} target="_blank" rel="noreferrer">
            {link.long_url} <Icon name="external" size={14} />
          </a>
          <div className="hero-actions">
            <CopyButton text={link.short_url} />
            <button className="btn secondary" onClick={() => setShowQr(true)}>
              <Icon name="qr" /> QR
            </button>
          </div>
        </div>

        <div className="hero-clicks">
          <div className="huge-number">{fmtNumber(stats.total)}</div>
          <div className="muted">total clicks</div>
        </div>

        <div className="hero-meta">
          <label className="meta-field">
            <span className="card-label">Label</span>
            <input value={label} maxLength={100} placeholder="Set label" onChange={(e) => setLabel(e.target.value)} />
          </label>
          <div className="meta-grid">
            <div>
              <span className="card-label">Created</span>
              <div>{fmtDateTime(link.created_at)}</div>
            </div>
            <label className="meta-field">
              <span className="card-label">Expires at</span>
              <input type="datetime-local" value={expires} onChange={(e) => setExpires(e.target.value)} />
            </label>
          </div>
          {dirty && (
            <div className="save-row">
              <button className="btn primary small-btn" onClick={save} disabled={saving}>
                {saving ? "Saving…" : "Save changes"}
              </button>
            </div>
          )}
          {saveMsg && <div className="muted small">{saveMsg}</div>}
        </div>
      </section>

      {/* slug */}
      <section className="card">
        <h3 className="card-label">Slug</h3>
        <div className="slug-row">
          <CopyButton text={link.short_url} variant="ghost" iconOnly />
          <button className="btn ghost icon-only" title="QR code" onClick={() => setShowQr(true)}>
            <Icon name="qr" />
          </button>
          <span className="mono slug-code">{link.code}</span>
          <span className="badge">{link.is_custom ? "CUSTOM" : "AUTO"}</span>
          <span className="bar-track grow">
            <span className="bar-fill orange" style={{ width: stats.total ? "100%" : "3%" }} />
          </span>
          <span className="bar-num">{fmtNumber(stats.total)}</span>
        </div>
        <p className="muted small mono">{link.short_url}</p>
      </section>

      <ClicksChart byDay={stats.by_day} title="Clicks over time (last 30 days)" />

      <div className="grid-2">
        <BarList title="Referrer hosts" items={stats.referrers} tone="green" />
        <BarList title="Access method" items={stats.sources} />
      </div>
      <div className="grid-2">
        <BarList title="Devices" items={stats.devices} />
        <BarList title="Browsers" items={stats.browsers} tone="green" />
      </div>

      {showQr && <QRModal link={link} onClose={() => setShowQr(false)} />}
    </>
  );
}

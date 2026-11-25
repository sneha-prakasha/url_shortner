import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import CopyButton from "../components/CopyButton";
import CreateLinkModal from "../components/CreateLinkModal";
import { Icon } from "../components/Icon";
import QRModal from "../components/QRModal";
import { fmtDate, fmtNumber, statusOf, stripProtocol } from "../format";

export default function Links() {
  const navigate = useNavigate();
  const [links, setLinks] = useState(null);
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);
  const [qrLink, setQrLink] = useState(null);

  useEffect(() => {
    api("/links").then(setLinks).catch((e) => setError(e.message));
  }, []);

  return (
    <>
      <header className="page-head">
        <h1>Links</h1>
        <button className="btn primary" onClick={() => setCreating(true)}>
          <Icon name="plus" /> New link
        </button>
      </header>

      {error && <p className="error">{error}</p>}
      {!links && !error && <p className="muted">Loading…</p>}

      {links && links.length === 0 && (
        <div className="card empty">
          <h2>No links yet</h2>
          <p className="muted">Paste a long URL and get a short one you can track.</p>
          <button className="btn primary" onClick={() => setCreating(true)}>
            <Icon name="plus" /> Create your first link
          </button>
        </div>
      )}

      {links && links.length > 0 && (
        <ul className="link-list">
          {links.map((l) => {
            const status = statusOf(l);
            return (
              <li key={l.id} className="card link-row">
                <Link to={`/links/${l.id}`} className="link-main">
                  <div className="link-title">
                    <strong>{l.label || l.code}</strong>
                    <span className={`pill ${status.tone}`}>{status.label}</span>
                  </div>
                  <div className="mono short">{stripProtocol(l.short_url)}</div>
                  <div className="muted small ellipsis">{l.long_url}</div>
                  <div className="muted small">Created {fmtDate(l.created_at)}</div>
                </Link>
                <div className="link-clicks">
                  <div className="num">{fmtNumber(l.clicks)}</div>
                  <div className="muted small">clicks</div>
                </div>
                <div className="link-actions">
                  <CopyButton text={l.short_url} variant="secondary" iconOnly />
                  <button
                    className="btn secondary icon-only"
                    title="QR code"
                    onClick={() => setQrLink(l)}
                  >
                    <Icon name="qr" />
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {creating && (
        <CreateLinkModal
          onClose={() => setCreating(false)}
          onCreated={(link) => navigate(`/links/${link.id}`)}
        />
      )}
      {qrLink && <QRModal link={qrLink} onClose={() => setQrLink(null)} />}
    </>
  );
}

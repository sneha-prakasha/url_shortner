import { useEffect } from "react";
import { Icon } from "./Icon";

export default function QRModal({ link, onClose }) {
  // close with the Escape key
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const src = `/api/qr/${link.code}.svg`;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal small" onClick={(e) => e.stopPropagation()} role="dialog" aria-label="QR code">
        <div className="modal-head">
          <h2>QR code</h2>
          <button className="btn ghost icon-only" onClick={onClose} aria-label="Close">
            <Icon name="x" />
          </button>
        </div>
        <div className="qr-box">
          <img src={src} alt={`QR code for ${link.short_url}`} />
        </div>
        <p className="muted small center mono">{link.short_url}</p>
        <a className="btn primary block" href={src} download={`${link.code}-qr.svg`}>
          Download SVG
        </a>
      </div>
    </div>
  );
}

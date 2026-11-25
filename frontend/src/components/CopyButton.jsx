import { useState } from "react";
import { Icon } from "./Icon";

// navigator.clipboard only works on https or localhost. On a plain http server
// (like an EC2 public IP) we fall back to the old textarea trick.
async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    let ok = false;
    try { ok = document.execCommand("copy"); } catch { ok = false; }
    document.body.removeChild(ta);
    return ok;
  }
}

export default function CopyButton({ text, variant = "primary", label = "Copy", iconOnly = false }) {
  const [copied, setCopied] = useState(false);

  async function onClick(e) {
    e.preventDefault();
    e.stopPropagation();
    if (await copyText(text)) {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }
  }

  return (
    <button
      className={`btn ${variant} ${iconOnly ? "icon-only" : ""}`}
      onClick={onClick}
      title={iconOnly ? "Copy short link" : undefined}
    >
      <Icon name={copied ? "check" : "copy"} />
      {!iconOnly && (copied ? "Copied!" : label)}
    </button>
  );
}

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import BarList from "../components/BarList";
import ClicksChart from "../components/ClicksChart";
import { fmtNumber, stripProtocol } from "../format";

function Stat({ label, value }) {
  return (
    <div className="card stat">
      <h3 className="card-label">{label}</h3>
      <div className="big-number">{fmtNumber(value)}</div>
    </div>
  );
}

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/overview").then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!data) return <p className="muted">Loading…</p>;

  const { stats } = data;

  return (
    <>
      <header className="page-head">
        <h1>Dashboard</h1>
      </header>

      <div className="grid-3">
        <Stat label="Total links" value={data.total_links} />
        <Stat label="Total clicks" value={data.total_clicks} />
        <Stat label="Clicks, last 7 days" value={data.clicks_7d} />
      </div>

      <ClicksChart byDay={stats.by_day} title="Clicks, last 30 days" />

      <div className="grid-2">
        <section className="card">
          <h3 className="card-label">Top links</h3>
          {data.top_links.length === 0 ? (
            <p className="muted small">
              No links yet. <Link to="/links">Create your first one</Link>.
            </p>
          ) : (
            <ul className="top-list">
              {data.top_links.map((l) => (
                <li key={l.id}>
                  <Link to={`/links/${l.id}`}>
                    <span className="top-name">{l.label || l.code}</span>
                    <span className="muted mono small">{stripProtocol(l.short_url)}</span>
                  </Link>
                  <strong>{fmtNumber(l.clicks)}</strong>
                </li>
              ))}
            </ul>
          )}
        </section>
        <BarList title="Referrer hosts" items={stats.referrers} tone="green" />
      </div>

      <div className="grid-2">
        <BarList title="Devices" items={stats.devices} />
        <BarList title="Access method" items={stats.sources} />
      </div>
    </>
  );
}

import { fmtNumber } from "../format";

// Horizontal bars: label | bar | number  (referrers, devices, browsers, ...)
export default function BarList({ title, items, tone = "orange", empty = "No clicks yet" }) {
  const max = Math.max(1, ...items.map((i) => i.count));
  return (
    <section className="card">
      <h3 className="card-label">{title}</h3>
      {items.length === 0 ? (
        <p className="muted small">{empty}</p>
      ) : (
        <ul className="bars">
          {items.map((item) => (
            <li key={item.name}>
              <span className="bar-name" title={item.name}>{item.name}</span>
              <span className="bar-track">
                <span
                  className={`bar-fill ${tone}`}
                  style={{ width: `${Math.max(3, (item.count / max) * 100)}%` }}
                />
              </span>
              <span className="bar-num">{fmtNumber(item.count)}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

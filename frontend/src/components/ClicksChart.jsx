import {
  BarElement, CategoryScale, Chart as ChartJS, LinearScale, Tooltip,
} from "chart.js";
import { Bar } from "react-chartjs-2";
import { fmtDay } from "../format";

ChartJS.register(BarElement, CategoryScale, LinearScale, Tooltip);

const ORANGE = "#ff6f31";
const MUTED = "#8a95a6";

// Bar chart of clicks per day (Chart.js via react-chartjs-2)
export default function ClicksChart({ byDay, title = "Clicks over time" }) {
  const data = {
    labels: byDay.map((d) => fmtDay(d.date)),
    datasets: [
      {
        label: "Clicks",
        data: byDay.map((d) => d.clicks),
        backgroundColor: ORANGE,
        hoverBackgroundColor: "#ff8a57",
        borderRadius: 4,
        borderSkipped: false,
        maxBarThickness: 22,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: "#0b1219",
        titleColor: "#f2f5f8",
        bodyColor: "#f2f5f8",
        borderColor: "#2a3547",
        borderWidth: 1,
        padding: 10,
        displayColors: false,
        callbacks: { label: (ctx) => `${ctx.parsed.y} click${ctx.parsed.y === 1 ? "" : "s"}` },
      },
    },
    scales: {
      x: {
        grid: { display: false },
        border: { display: false },
        ticks: { color: MUTED, maxTicksLimit: 6, maxRotation: 0 },
      },
      y: {
        beginAtZero: true,
        grid: { color: "rgba(138,149,166,0.12)" },
        border: { display: false },
        ticks: { color: MUTED, precision: 0, maxTicksLimit: 5 },
      },
    },
  };

  return (
    <section className="card">
      <h3 className="card-label">{title}</h3>
      <div className="chart-box">
        <Bar data={data} options={options} />
      </div>
    </section>
  );
}

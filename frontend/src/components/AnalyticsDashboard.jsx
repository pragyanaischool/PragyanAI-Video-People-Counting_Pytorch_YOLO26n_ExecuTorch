import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { ChartNoAxesColumn, Timer, UserRoundCheck } from "lucide-react";
import { formatDuration } from "../utils/formatters";

export default function AnalyticsDashboard({ analytics }) {
  if (!analytics) return null;
  const data = [
    { name: "People", count: analytics.last_frame_people_count || 0 },
    { name: "Objects", count: analytics.last_frame_objects_count || 0 },
    { name: "Unique", count: analytics.unique_people_tracked || 0 }
  ];

  return (
    <section className="panel analytics-panel">
      <div className="section-heading">
        <div><span className="eyebrow">VIDEO SUMMARY</span><h2>Analytics dashboard</h2></div>
        <div className="heading-icon"><ChartNoAxesColumn size={21} /></div>
      </div>
      <div className="summary-grid">
        <div><span><UserRoundCheck size={16} /> Unique people</span><strong>{analytics.unique_people_tracked}</strong></div>
        <div><span><ChartNoAxesColumn size={16} /> Total frames</span><strong>{analytics.total_frames}</strong></div>
        <div><span><Timer size={16} /> Processing time</span><strong>{formatDuration(analytics.processing_seconds)}</strong></div>
      </div>
      <div className="chart-wrap">
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="name" />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="count" fill="#3478f6" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="muted">The People and Objects values represent the final processed frame; Unique represents distinct person tracking IDs observed during this run.</p>
    </section>
  );
}

import { Activity, Clock3, Gauge, LoaderCircle } from "lucide-react";
import { formatDuration, formatPercent } from "../utils/formatters";

export default function ProcessingStatus({ job }) {
  const progress = Number(job?.progress || 0);
  const status = job?.status || "idle";
  const activities = [...(job?.recent_activity || [])].reverse();

  return (
    <section className="panel status-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">PROCESSING STATUS</span>
          <h2>Video analysis</h2>
        </div>
        <span className={`status-pill ${status}`}>
          {status === "processing" && <LoaderCircle size={14} className="spin" />}
          {status}
        </span>
      </div>

      <div className="progress-meta">
        <strong>Frame {job?.current_frame || 0}</strong>
        <strong>{formatPercent(progress)}</strong>
      </div>
      <div className="progress-track"><div className="progress-fill" style={{ width: `${progress}%` }} /></div>

      <div className="status-details">
        <div><Clock3 size={16} /><span>Elapsed</span><b>{formatDuration(job?.elapsed_seconds)}</b></div>
        <div><Gauge size={16} /><span>Inference frames</span><b>{job?.frames_processed || 0}</b></div>
      </div>

      {job?.error && <div className="alert error">{job.error}</div>}

      <div className="latest-frame">
        <div className="subheading"><Activity size={16} /> Latest processed frame</div>
        {job?.latest_frame
          ? <img src={job.latest_frame} alt="Latest annotated video frame" />
          : <div className="frame-placeholder">Waiting for the first frame update…</div>}
      </div>

      <div className="activity-list">
        <div className="subheading">Recent frame activity <span>{activities.length} updates</span></div>
        {activities.length === 0
          ? <p className="muted">Frame-level updates will appear here.</p>
          : activities.slice(0, 8).map((item, index) => (
            <div className="activity-row" key={`${item.frame_number}-${index}`}>
              <span>Frame {item.frame_number}</span>
              <span>{item.people_count} people</span>
              <span>{item.objects_count} objects</span>
              <span>{item.unique_people} unique</span>
            </div>
          ))}
      </div>
    </section>
  );
}

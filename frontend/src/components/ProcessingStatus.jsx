import {
  Activity,
  Clock3,
  Gauge,
  LoaderCircle,
  ScanSearch,
  Users,
  Fingerprint,
} from "lucide-react";
import { formatDuration, formatPercent } from "../utils/formatters";

export default function ProcessingStatus({ job }) {
  const progress = Number(job?.progress || 0);
  const status = job?.status || "idle";
  const activities = [...(job?.recent_activity || [])].reverse();
  const detections = job?.current_detections || [];

  return (
    <section className="panel status-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">LIVE PROCESSING</span>
          <h2>Video analysis</h2>
        </div>
        <span className={`status-pill ${status}`}>
          {status === "processing" && <LoaderCircle size={14} className="spin" />}
          {status}
        </span>
      </div>

      <div className="progress-meta">
        <strong>
          Frame {job?.current_frame || 0}
          {job?.total_frames ? ` / ${job.total_frames}` : ""}
        </strong>
        <strong>{formatPercent(progress)}</strong>
      </div>
      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${progress}%` }} />
      </div>

      <div className="live-stage">
        <b>{String(job?.stage || "queued").replaceAll("_", " ")}</b>
        <p>{job?.activity_message || "Waiting for processing updates…"}</p>
      </div>

      <div className="status-details">
        <div><Clock3 size={16} /><span>Elapsed</span><b>{formatDuration(job?.elapsed_seconds)}</b></div>
        <div><Gauge size={16} /><span>Inference frames</span><b>{job?.frames_processed || 0}</b></div>
        <div><Users size={16} /><span>People now</span><b>{job?.current_people || 0}</b></div>
        <div><Fingerprint size={16} /><span>Unique people</span><b>{job?.unique_people_so_far || 0}</b></div>
      </div>

      {job?.error && <div className="alert error">{job.error}</div>}

      <div className="latest-frame">
        <div className="subheading"><Activity size={16} /> Latest processed frame</div>
        {job?.latest_frame
          ? <img src={job.latest_frame} alt="Latest annotated video frame" />
          : <div className="frame-placeholder">Waiting for the first annotated frame…</div>}
      </div>

      <div className="detection-live">
        <div className="subheading">
          <ScanSearch size={16} />
          Current frame detections
          <span>{detections.length} objects</span>
        </div>
        {detections.length === 0 ? (
          <p className="muted">No detections reported for the current frame.</p>
        ) : (
          <div className="detection-list">
            {detections.slice(0, 30).map((item, index) => (
              <div className="detection-row" key={`${item.track_id ?? "untracked"}-${index}`}>
                <b>{item.class_name || `Class ${item.class_id}`}</b>
                <span>{item.is_person ? "Person" : "Object"}</span>
                <span>{item.track_id == null ? "No ID" : `ID ${item.track_id}`}</span>
                <span>{item.confidence == null ? "—" : `${(item.confidence * 100).toFixed(1)}%`}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="activity-list">
        <div className="subheading">Frame-by-frame activity <span>{activities.length} latest frames</span></div>
        {activities.length === 0
          ? <p className="muted">Frame events will appear here as processing advances.</p>
          : activities.slice(0, 15).map((item) => (
            <div className="activity-row" key={item.frame_number}>
              <span>Frame {item.frame_number}</span>
              <span>{item.people_count} people</span>
              <span>{item.objects_count} objects</span>
              <span>{item.unique_people} unique</span>
              <span>{item.inference_performed ? "YOLO" : "carried"}</span>
            </div>
          ))}
      </div>
    </section>
  );
}


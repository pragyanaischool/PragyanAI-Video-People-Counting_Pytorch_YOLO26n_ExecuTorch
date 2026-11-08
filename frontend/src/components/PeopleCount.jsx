import { Users, Scan, Fingerprint, Images } from "lucide-react";

function Metric({ icon: Icon, label, value, note }) {
  return (
    <div className="metric-card">
      <div className="metric-top"><span>{label}</span><span className="metric-icon"><Icon size={18} /></span></div>
      <strong>{value ?? 0}</strong>
      <small>{note}</small>
    </div>
  );
}

export default function PeopleCount({ job }) {
  return (
    <div className="metrics-grid">
      <Metric icon={Users} label="People in current frame" value={job?.current_people} note="Person class detections" />
      <Metric icon={Scan} label="Objects in current frame" value={job?.current_objects} note="All detected classes" />
      <Metric icon={Fingerprint} label="Unique people tracked" value={job?.unique_people_so_far} note="Distinct ByteTrack IDs observed" />
      <Metric icon={Images} label="Frames processed" value={job?.frames_processed} note={job?.total_frames ? `of ${job.total_frames} total frames` : "Inference frames"} />
    </div>
  );
}

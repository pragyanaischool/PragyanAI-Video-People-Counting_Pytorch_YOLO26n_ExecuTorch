import { Download, Film, FileSpreadsheet, FileJson } from "lucide-react";
import { getDownloadUrl } from "../services/api";

function DownloadLink({ href, icon: Icon, label }) {
  return (
    <a className="download-link" href={href}>
      <Icon size={17} /> {label} <Download size={15} />
    </a>
  );
}

export default function VideoPreview({ job }) {
  if (job?.status !== "completed") return null;
  return (
    <section className="panel">
      <div className="section-heading">
        <div><span className="eyebrow">OUTPUTS</span><h2>Processed video & reports</h2></div>
        <div className="heading-icon"><Film size={21} /></div>
      </div>
      <video className="result-video" controls preload="metadata" src={getDownloadUrl(job.job_id, "video")} />
      <div className="download-grid">
        <DownloadLink href={getDownloadUrl(job.job_id, "video")} icon={Film} label="Download MP4" />
        <DownloadLink href={getDownloadUrl(job.job_id, "csv")} icon={FileSpreadsheet} label="Download CSV" />
        <DownloadLink href={getDownloadUrl(job.job_id, "json")} icon={FileJson} label="Download JSON" />
      </div>
    </section>
  );
}

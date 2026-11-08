import { useEffect, useState } from "react";
import { Activity, Cpu, ShieldCheck, Video } from "lucide-react";
import VideoUpload from "./components/VideoUpload";
import ProcessingStatus from "./components/ProcessingStatus";
import PeopleCount from "./components/PeopleCount";
import VideoPreview from "./components/VideoPreview";
import AnalyticsDashboard from "./components/AnalyticsDashboard";
import { createVideoJob, getJobStatus, getJobAnalytics, healthCheck } from "./services/api";

export default function App() {
  const [job, setJob] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [busy, setBusy] = useState(false);
  const [backend, setBackend] = useState("checking");
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    healthCheck()
      .then((data) => active && setBackend(data.model_files_present ? "ready" : "model-missing"))
      .catch(() => active && setBackend("offline"));
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!job?.job_id || !["queued", "processing"].includes(job.status)) return undefined;
    let active = true;
    let timer;
    const poll = async () => {
      try {
        const latest = await getJobStatus(job.job_id);
        if (!active) return;
        setJob(latest);
        if (latest.status === "completed") {
          const result = await getJobAnalytics(job.job_id);
          if (active) setAnalytics(result.analytics);
          return;
        }
        if (latest.status === "queued" || latest.status === "processing") {
          timer = setTimeout(poll, 3000);
        }
      } catch (err) {
        if (active) {
          setError(`Status check failed: ${err.message}`);
          timer = setTimeout(poll, 5000);
        }
      }
    };
    timer = setTimeout(poll, 500);
    return () => { active = false; clearTimeout(timer); };
  }, [job?.job_id, job?.status]);

  async function startJob({ file, confidence, frameInterval }) {
    setBusy(true);
    setError("");
    setAnalytics(null);
    setJob(null);
    try {
      const created = await createVideoJob(file, confidence, frameInterval);
      setJob({
        job_id: created.job_id,
        status: created.status,
        progress: 0,
        current_frame: 0,
        frames_processed: 0,
        current_people: 0,
        current_objects: 0,
        unique_people_so_far: 0,
        recent_activity: []
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const backendLabel = {
    checking: "Checking backend",
    ready: "Backend & model ready",
    "model-missing": "Backend online · model missing",
    offline: "Backend unavailable"
  }[backend];

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="/">
          <span className="brand-mark"><Cpu size={22} /></span>
          <span><strong>PragyanAI</strong><small>VIDEO INTELLIGENCE</small></span>
        </a>
        <div className={`backend-indicator ${backend}`}>
          <span /> {backendLabel}
        </div>
      </header>

      <section className="hero">
        <div className="hero-copy">
          <span className="hero-tag"><ShieldCheck size={14} /> AI-POWERED VIDEO ANALYTICS</span>
          <h1>People detection.<br /><em>Clear insights.</em></h1>
          <p>Upload a video to detect people and objects, track identities across frames, and generate downloadable analytics.</p>
        </div>
        <div className="hero-art"><Video size={68} strokeWidth={1.1} /><span>YOLO26n · ExecuTorch · ByteTrack</span></div>
      </section>

      {error && <div className="alert error global-alert">{error}</div>}

      <section className="main-grid">
        <div className="left-column">
          <VideoUpload onSubmit={startJob} busy={busy} />
          {job && <PeopleCount job={job} />}
          {analytics && <AnalyticsDashboard analytics={analytics} />}
          <VideoPreview job={job} />
        </div>
        <div className="right-column">
          <ProcessingStatus job={job} />
          <div className="panel workflow-panel">
            <div className="subheading"><Activity size={16} /> Processing pipeline</div>
            <div className="pipeline-item"><span>01</span><div><b>Frame extraction</b><small>OpenCV video reader</small></div></div>
            <div className="pipeline-item"><span>02</span><div><b>Object detection</b><small>YOLO26n ExecuTorch</small></div></div>
            <div className="pipeline-item"><span>03</span><div><b>Multi-object tracking</b><small>ByteTrack identities</small></div></div>
            <div className="pipeline-item"><span>04</span><div><b>Analytics & export</b><small>MP4 · CSV · JSON</small></div></div>
          </div>
        </div>
      </section>

      <footer><span>© {new Date().getFullYear()} PragyanAI</span><span>YOLO26n · ExecuTorch · FastAPI · React</span></footer>
    </main>
  );
}

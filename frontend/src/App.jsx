
import { useEffect, useState } from "react";

import {
  Activity,
  Cpu,
  ShieldCheck,
  Video,
  Wifi,
  WifiOff,
  AlertCircle
} from "lucide-react";

// --------------------------------------------------
// COMPONENT IMPORTS
// --------------------------------------------------

import VideoUpload from "./components/VideoUpload";
import ProcessingStatus from "./components/ProcessingStatus";
import PeopleCount from "./components/PeopleCount";
import VideoPreview from "./components/VideoPreview";
import AnalyticsDashboard from "./components/AnalyticsDashboard";

// --------------------------------------------------
// API IMPORTS
// --------------------------------------------------

import {
  createVideoJob,
  getJobAnalytics,
  healthCheck,
  subscribeJobEvents
} from "./services/api";


// --------------------------------------------------
// APPLICATION
// --------------------------------------------------

export default function App() {

  // ------------------------------------------------
  // STATE MANAGEMENT
  // ------------------------------------------------

  const [job, setJob] = useState(null);

  const [analytics, setAnalytics] = useState(null);

  const [busy, setBusy] = useState(false);

  const [backend, setBackend] = useState("checking");

  const [error, setError] = useState("");


  // ------------------------------------------------
  // 1. CHECK BACKEND CONNECTION
  // ------------------------------------------------

  useEffect(() => {

    let active = true;

    async function checkBackend() {

      try {

        const response = await healthCheck();

        if (!active) return;

        if (!response.backend_connected) {
          setBackend("offline");
        } else if (response.model_loaded) {
          setBackend("ready");
        } else if (response.model_files_present) {
          // Model files exist, but model initialization failed.
          setBackend("model-error");
        } else {
          setBackend("model-missing");
        }

      } catch (err) {

        if (active) {

          console.error("Backend health check failed:", err);

          setBackend("offline");

        }

      }

    }

    checkBackend();

    return () => {

      active = false;

    };

  }, []);


  // ------------------------------------------------
  // 2. CREATE VIDEO PROCESSING JOB
  // ------------------------------------------------

  async function startJob({
    file,
    confidence,
    frameInterval
  }) {

    if (!file) {

      setError("Please select a video file.");

      return;

    }

    setBusy(true);

    setError("");

    setAnalytics(null);

    setJob(null);

    try {

      // Upload video and create processing job
      const created = await createVideoJob(
        file,
        confidence,
        frameInterval
      );

      // Initialize job state
      setJob({

        job_id: created.job_id,

        status: created.status || "queued",

        progress: 0,

        current_frame: 0,

        total_frames: null,

        frames_processed: 0,

        current_people: 0,

        current_objects: 0,

        unique_people_so_far: 0,

        elapsed_seconds: 0,

        latest_frame: null,

        recent_activity: [],

        error: null

      });

    } catch (err) {

      console.error("Video upload failed:", err);

      setError(
        err.message || "Unable to upload video. Please try again."
      );

    } finally {

      setBusy(false);

    }

  }


  // ------------------------------------------------
  // 3. LIVE VIDEO PROCESSING UPDATES (SSE)
  // ------------------------------------------------

  useEffect(() => {
    if (!job?.job_id) return undefined;

    let active = true;
    let analyticsLoaded = false;

    const stream = subscribeJobEvents(
      job.job_id,
      async (latest) => {
        if (!active) return;

        setJob((previous) => ({
          ...previous,
          ...latest,
        }));

        if (latest.status === "completed" && !analyticsLoaded) {
          analyticsLoaded = true;
          try {
            const result = await getJobAnalytics(job.job_id);
            if (active) setAnalytics(result.analytics);
          } catch (analyticsError) {
            if (active) {
              setError(
                `Video completed, but analytics could not be loaded: ${analyticsError.message}`
              );
            }
          }
        }

        if (latest.status === "failed") {
          setError(latest.error || "Video processing failed.");
        } else if (latest.status === "processing" || latest.status === "completed") {
          setError("");
        }
      },
      (streamError) => {
        if (active) {
          setError(
            `${streamError.message} The job may still be running; refresh the page or reconnect to its job stream.`
          );
        }
      }
    );

    return () => {
      active = false;
      stream.close();
    };
  }, [job?.job_id]);


  // ------------------------------------------------
  // 4. BACKEND STATUS LABEL
  // ------------------------------------------------

  const backendLabel = {

    checking: "Checking backend",

    ready: "Backend & model ready",

    "model-missing": "Backend online · Model files missing",

    "model-error": "Backend online · Model failed to load",

    offline: "Backend unavailable"

  }[backend] || "Unknown status";


  // ------------------------------------------------
  // 5. BACKEND STATUS ICON
  // ------------------------------------------------

  const BackendIcon =

    backend === "ready"
      ? Wifi
      : backend === "offline"
        ? WifiOff
        : Activity;


  // ------------------------------------------------
  // 6. APPLICATION UI
  // ------------------------------------------------

  return (

    <main className="app-shell">


      {/* ========================================== */}
      {/* HEADER                                     */}
      {/* ========================================== */}

      <header className="topbar">

        <a
          className="brand"
          href="/"
        >

          <span className="brand-mark">

            <Cpu size={22} />

          </span>

          <span>

            <strong>
              PragyanAI
            </strong>

            <small>
              VIDEO INTELLIGENCE
            </small>

          </span>

        </a>


        {/* BACKEND CONNECTION STATUS */}

        <div
          className={`backend-indicator ${backend}`}
          title={backendLabel}
        >

          <BackendIcon size={15} />

          <span />

          {backendLabel}

        </div>

      </header>


      {/* ========================================== */}
      {/* HERO SECTION                               */}
      {/* ========================================== */}

      <section className="hero">

        <div className="hero-copy">

          <span className="hero-tag">

            <ShieldCheck size={14} />

            AI-POWERED VIDEO ANALYTICS

          </span>

          <h1>

            People detection.

            <br />

            <em>
              Clear insights.
            </em>

          </h1>

          <p>

            Upload a video to detect people and objects,
            track identities across frames, and generate
            downloadable analytics.

          </p>

        </div>


        <div className="hero-art">

          <Video
            size={68}
            strokeWidth={1.1}
          />

          <span>
            YOLO26n · ExecuTorch · ByteTrack
          </span>

        </div>

      </section>


      {/* ========================================== */}
      {/* GLOBAL ERROR MESSAGE                       */}
      {/* ========================================== */}

      {error && (

        <div
          className="alert error global-alert"
          role="alert"
        >

          <AlertCircle size={17} />

          <span>
            {error}
          </span>

        </div>

      )}


      {/* ========================================== */}
      {/* MAIN APPLICATION GRID                      */}
      {/* ========================================== */}

      <section className="main-grid">


        {/* ---------------------------------------- */}
        {/* LEFT COLUMN                              */}
        {/* ---------------------------------------- */}

        <div className="left-column">


          {/* VIDEO UPLOAD */}

          <VideoUpload

            onSubmit={startJob}

            busy={busy}

          />


          {/* PEOPLE AND OBJECT COUNTS */}

          {job && (

            <PeopleCount
              job={job}
            />

          )}


          {/* ANALYTICS DASHBOARD */}

          {analytics && (

            <AnalyticsDashboard
              analytics={analytics}
            />

          )}


          {/* PROCESSED VIDEO AND DOWNLOADS */}

          <VideoPreview
            job={job}
          />


        </div>


        {/* ---------------------------------------- */}
        {/* RIGHT COLUMN                             */}
        {/* ---------------------------------------- */}

        <div className="right-column">


          {/* PROCESSING STATUS */}

          <ProcessingStatus
            job={job}
          />


          {/* PROCESSING PIPELINE */}

          <div className="panel workflow-panel">

            <div className="subheading">

              <Activity size={16} />

              Processing pipeline

            </div>


            <div className="pipeline-item">

              <span>01</span>

              <div>

                <b>
                  Frame extraction
                </b>

                <small>
                  OpenCV video reader
                </small>

              </div>

            </div>


            <div className="pipeline-item">

              <span>02</span>

              <div>

                <b>
                  Object detection
                </b>

                <small>
                  YOLO26n ExecuTorch
                </small>

              </div>

            </div>


            <div className="pipeline-item">

              <span>03</span>

              <div>

                <b>
                  Multi-object tracking
                </b>

                <small>
                  ByteTrack identities
                </small>

              </div>

            </div>


            <div className="pipeline-item">

              <span>04</span>

              <div>

                <b>
                  Analytics & export
                </b>

                <small>
                  MP4 · CSV · JSON
                </small>

              </div>

            </div>

          </div>


          {/* TECHNOLOGY INFORMATION */}

          <div className="panel technology-panel">

            <div className="subheading">

              <Cpu size={16} />

              Technology stack

            </div>

            <div className="technology-tags">

              <span>YOLO26n</span>

              <span>ExecuTorch</span>

              <span>ByteTrack</span>

              <span>OpenCV</span>

              <span>FastAPI</span>

              <span>React</span>

            </div>

          </div>


        </div>

      </section>


      {/* ========================================== */}
      {/* FOOTER                                     */}
      {/* ========================================== */}

      <footer>

        <span>

          © {new Date().getFullYear()} PragyanAI

        </span>

        <span>

          YOLO26n · ExecuTorch · FastAPI · React

        </span>

      </footer>


    </main>

  );

}


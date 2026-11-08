
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
  getJobStatus,
  getJobAnalytics,
  healthCheck
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

        if (response.model_files_present) {

          setBackend("ready");

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
  // 3. POLL VIDEO PROCESSING STATUS
  // ------------------------------------------------

  useEffect(() => {

    if (!job?.job_id) {

      return undefined;

    }

    // Poll only while the job is active
    if (!["queued", "processing"].includes(job.status)) {

      return undefined;

    }

    let active = true;

    let timer = null;


    async function pollJobStatus() {

      try {

        const latest = await getJobStatus(job.job_id);

        if (!active) return;

        // Update real-time job information
        setJob(latest);

        setError("");

        // ------------------------------------------
        // PROCESSING COMPLETED
        // ------------------------------------------

        if (latest.status === "completed") {

          try {

            const result = await getJobAnalytics(job.job_id);

            if (active) {

              setAnalytics(result.analytics);

            }

          } catch (analyticsError) {

            console.error(
              "Analytics retrieval failed:",
              analyticsError
            );

            if (active) {

              setError(
                `Video completed, but analytics could not be loaded: ${analyticsError.message}`
              );

            }

          }

          return;

        }


        // ------------------------------------------
        // PROCESSING FAILED
        // ------------------------------------------

        if (latest.status === "failed") {

          setError(
            latest.error || "Video processing failed."
          );

          return;

        }


        // ------------------------------------------
        // PROCESSING CONTINUES
        // ------------------------------------------

        if (
          latest.status === "queued" ||
          latest.status === "processing"
        ) {

          timer = setTimeout(
            pollJobStatus,
            3000
          );

        }

      } catch (err) {

        console.error(
          "Job status polling error:",
          err
        );

        if (active) {

          setError(
            `Status check failed: ${err.message}`
          );

          // Retry after 5 seconds
          timer = setTimeout(
            pollJobStatus,
            5000
          );

        }

      }

    }


    // Initial status check
    timer = setTimeout(
      pollJobStatus,
      500
    );


    // Cleanup polling timer
    return () => {

      active = false;

      if (timer) {

        clearTimeout(timer);

      }

    };

  }, [job?.job_id, job?.status]);


  // ------------------------------------------------
  // 4. BACKEND STATUS LABEL
  // ------------------------------------------------

  const backendLabel = {

    checking: "Checking backend",

    ready: "Backend & model ready",

    "model-missing": "Backend online · Model missing",

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

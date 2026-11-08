
import { useRef, useState } from "react";
import {
  FileVideo,
  UploadCloud,
  X,
  Play,
  AlertCircle,
  CheckCircle
} from "lucide-react";

import { formatBytes } from "../utils/formatters";

// --------------------------------------------------
// CONFIGURATION
// --------------------------------------------------

const ACCEPTED = ".mp4,.avi,.mov,.mkv,.webm";

const MAX_BYTES = 500 * 1024 * 1024; // 500 MB

const ALLOWED_EXTENSIONS = [
  "mp4",
  "avi",
  "mov",
  "mkv",
  "webm"
];

// --------------------------------------------------
// VIDEO UPLOAD COMPONENT
// --------------------------------------------------

export default function VideoUpload({ onSubmit, busy }) {

  const inputRef = useRef(null);

  const [file, setFile] = useState(null);

  const [confidence, setConfidence] = useState(0.35);

  const [frameInterval, setFrameInterval] = useState(3);

  const [error, setError] = useState("");

  const [isDragging, setIsDragging] = useState(false);


  // ------------------------------------------------
  // FILE VALIDATION
  // ------------------------------------------------

  function selectFile(candidate) {

    setError("");

    if (!candidate) return;

    // Validate file extension
    const extension = candidate.name
      .split(".")
      .pop()
      .toLowerCase();

    if (!ALLOWED_EXTENSIONS.includes(extension)) {

      setError(
        "Choose an MP4, AVI, MOV, MKV or WEBM video."
      );

      return;
    }

    // Validate file size
    if (candidate.size > MAX_BYTES) {

      setError(
        "Maximum upload size is 500 MB."
      );

      return;
    }

    if (candidate.size === 0) {

      setError(
        "The selected video file is empty."
      );

      return;
    }

    setFile(candidate);

    // Reset file input so the same file can be selected again
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }


  // ------------------------------------------------
  // REMOVE SELECTED FILE
  // ------------------------------------------------

  function removeFile() {

    setFile(null);

    setError("");

    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }


  // ------------------------------------------------
  // FORM SUBMISSION
  // ------------------------------------------------

  function submit(event) {

    event.preventDefault();

    setError("");

    if (busy) return;

    if (!file) {

      setError(
        "Please select a video first."
      );

      return;
    }

    // Send selected video and inference parameters
    onSubmit({
      file,
      confidence,
      frameInterval
    });
  }


  // ------------------------------------------------
  // DRAG AND DROP HANDLERS
  // ------------------------------------------------

  function handleDragOver(event) {

    event.preventDefault();

    if (!busy) {
      setIsDragging(true);
    }
  }


  function handleDragLeave(event) {

    event.preventDefault();

    setIsDragging(false);
  }


  function handleDrop(event) {

    event.preventDefault();

    setIsDragging(false);

    if (busy) return;

    const droppedFile = event.dataTransfer.files?.[0];

    selectFile(droppedFile);
  }


  // ------------------------------------------------
  // COMPONENT UI
  // ------------------------------------------------

  return (

    <form
      className="panel upload-panel"
      onSubmit={submit}
    >

      {/* ------------------------------------------ */}
      {/* HEADER                                     */}
      {/* ------------------------------------------ */}

      <div className="section-heading">

        <div>

          <span className="eyebrow">
            INPUT VIDEO
          </span>

          <h2>
            Upload a video
          </h2>

          <p>
            Analyze people and objects with
            YOLO26n and ByteTrack.
          </p>

        </div>

        <div className="heading-icon">
          <FileVideo size={21} />
        </div>

      </div>


      {/* ------------------------------------------ */}
      {/* VIDEO FILE INPUT                           */}
      {/* ------------------------------------------ */}

      <button
        type="button"
        className={`dropzone ${
          file ? "has-file" : ""
        } ${
          isDragging ? "dragging" : ""
        }`}
        disabled={busy}

        onClick={() => inputRef.current?.click()}

        onDragOver={handleDragOver}

        onDragLeave={handleDragLeave}

        onDrop={handleDrop}

      >

        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED}
          hidden
          disabled={busy}

          onChange={(event) => {
            selectFile(event.target.files?.[0]);
          }}
        />

        <span className="upload-icon">

          <UploadCloud size={27} />

        </span>

        <strong>

          {file
            ? file.name
            : isDragging
              ? "Drop your video here"
              : "Choose a video or drag it here"
          }

        </strong>

        <span>

          {file
            ? formatBytes(file.size)
            : "MP4, AVI, MOV, MKV or WEBM · Maximum 500 MB"
          }

        </span>

      </button>


      {/* ------------------------------------------ */}
      {/* SELECTED VIDEO                             */}
      {/* ------------------------------------------ */}

      {file && (

        <div className="selected-file">

          <div>

            <FileVideo size={17} />

            <span>
              {file.name}
            </span>

            <small>
              {formatBytes(file.size)}
            </small>

          </div>

          <button
            type="button"
            className="icon-button"
            onClick={removeFile}
            disabled={busy}
            aria-label="Remove selected video"
          >

            <X size={17} />

          </button>

        </div>

      )}


      {/* ------------------------------------------ */}
      {/* INFERENCE SETTINGS                         */}
      {/* ------------------------------------------ */}

      <div className="settings-grid">


        {/* CONFIDENCE THRESHOLD */}

        <label className="field">

          <span>

            Confidence threshold

            <b>
              {confidence.toFixed(2)}
            </b>

          </span>

          <input
            type="range"
            min="0.10"
            max="0.90"
            step="0.05"
            value={confidence}
            disabled={busy}

            onChange={(event) => {

              setConfidence(
                Number(event.target.value)
              );

            }}
          />

          <small>
            Higher values reduce low-confidence detections.
          </small>

        </label>


        {/* FRAME INTERVAL */}

        <label className="field">

          <span>
            Inference frame interval
          </span>

          <select
            value={frameInterval}
            disabled={busy}

            onChange={(event) => {

              setFrameInterval(
                Number(event.target.value)
              );

            }}
          >

            <option value="1">
              Every frame (best tracking)
            </option>

            <option value="2">
              Every 2 frames
            </option>

            <option value="3">
              Every 3 frames
            </option>

            <option value="5">
              Every 5 frames (faster)
            </option>

          </select>

          <small>
            Skipping frames can reduce tracking continuity.
          </small>

        </label>

      </div>


      {/* ------------------------------------------ */}
      {/* ERROR MESSAGE                              */}
      {/* ------------------------------------------ */}

      {error && (

        <div
          className="alert error"
          role="alert"
        >

          <AlertCircle size={17} />

          {error}

        </div>

      )}


      {/* ------------------------------------------ */}
      {/* SELECTED FILE STATUS                       */}
      {/* ------------------------------------------ */}

      {file && !error && (

        <div className="upload-ready">

          <CheckCircle size={16} />

          Video ready for processing

        </div>

      )}


      {/* ------------------------------------------ */}
      {/* SUBMIT BUTTON                              */}
      {/* ------------------------------------------ */}

      <button
        className="primary-button"
        type="submit"
        disabled={busy || !file}
      >

        <Play
          size={17}
          fill="currentColor"
        />

        {busy
          ? "Uploading..."
          : "Start people counting"
        }

      </button>

    </form>

  );

}

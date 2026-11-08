import { useRef, useState } from "react";
import { FileVideo, UploadCloud, X, Play } from "lucide-react";
import { formatBytes } from "../utils/formatters";

const ACCEPTED = ".mp4,.avi,.mov,.mkv,.webm";
const MAX_BYTES = 500 * 1024 * 1024;

export default function VideoUpload({ onSubmit, busy }) {
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [confidence, setConfidence] = useState(0.35);
  const [frameInterval, setFrameInterval] = useState(1);
  const [error, setError] = useState("");

  function selectFile(candidate) {
    setError("");
    if (!candidate) return;
    if (!/\.(mp4|avi|mov|mkv|webm)$/i.test(candidate.name)) {
      setError("Choose an MP4, AVI, MOV, MKV or WEBM video.");
      return;
    }
    if (candidate.size > MAX_BYTES) {
      setError("Maximum upload size is 500 MB.");
      return;
    }
    setFile(candidate);
  }

  function submit(event) {
    event.preventDefault();
    if (!file) {
      setError("Please select a video first.");
      return;
    }
    onSubmit({ file, confidence, frameInterval });
  }

  return (
    <form className="panel upload-panel" onSubmit={submit}>
      <div className="section-heading">
        <div>
          <span className="eyebrow">INPUT VIDEO</span>
          <h2>Upload a video</h2>
          <p>Analyze people and objects with YOLO26n and ByteTrack.</p>
        </div>
        <div className="heading-icon"><FileVideo size={21} /></div>
      </div>

      <button
        type="button"
        className={`dropzone ${file ? "has-file" : ""}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          selectFile(e.dataTransfer.files?.[0]);
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED}
          hidden
          onChange={(e) => selectFile(e.target.files?.[0])}
        />
        <span className="upload-icon"><UploadCloud size={27} /></span>
        <strong>{file ? file.name : "Choose a video or drag it here"}</strong>
        <span>{file ? formatBytes(file.size) : "MP4, AVI, MOV, MKV or WEBM · Maximum 500 MB"}</span>
      </button>

      {file && (
        <div className="selected-file">
          <div><FileVideo size={17} /><span>{file.name}</span><small>{formatBytes(file.size)}</small></div>
          <button type="button" className="icon-button" onClick={() => setFile(null)} aria-label="Remove file"><X size={17} /></button>
        </div>
      )}

      <div className="settings-grid">
        <label className="field">
          <span>Confidence threshold <b>{confidence.toFixed(2)}</b></span>
          <input type="range" min="0.10" max="0.90" step="0.05" value={confidence}
            onChange={(e) => setConfidence(Number(e.target.value))} />
          <small>Higher values reduce low-confidence detections.</small>
        </label>
        <label className="field">
          <span>Inference frame interval</span>
          <select value={frameInterval} onChange={(e) => setFrameInterval(Number(e.target.value))}>
            <option value="1">Every frame (best tracking)</option>
            <option value="2">Every 2 frames</option>
            <option value="3">Every 3 frames</option>
            <option value="5">Every 5 frames (faster)</option>
          </select>
          <small>Skipping frames can reduce tracking continuity.</small>
        </label>
      </div>

      {error && <div className="alert error">{error}</div>}
      <button className="primary-button" type="submit" disabled={busy || !file}>
        <Play size={17} fill="currentColor" /> {busy ? "Uploading..." : "Start people counting"}
      </button>
    </form>
  );
}

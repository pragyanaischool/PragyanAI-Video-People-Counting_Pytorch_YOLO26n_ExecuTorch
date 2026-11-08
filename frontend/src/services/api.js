const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000")
  .replace(/\/+$/, "");

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const message = typeof payload === "object"
      ? (payload.detail || payload.message || `Request failed (${response.status})`)
      : payload;
    throw new Error(message);
  }
  return payload;
}

export function getApiBaseUrl() {
  return API_BASE_URL;
}

export function healthCheck() {
  return request("/health");
}

export function getModelInfo() {
  return request("/api/model-info");
}

export function createVideoJob(file, confidence = 0.35, frameInterval = 1, onUploadProgress) {
  // Browser fetch does not expose upload progress without XHR. onUploadProgress is reserved for future use.
  const form = new FormData();
  form.append("file", file);
  form.append("confidence", String(confidence));
  form.append("frame_interval", String(frameInterval));
  return request("/api/jobs", { method: "POST", body: form });
}

export function getJobStatus(jobId) {
  return request(`/api/jobs/${encodeURIComponent(jobId)}`);
}

export function getJobAnalytics(jobId) {
  return request(`/api/jobs/${encodeURIComponent(jobId)}/analytics`);
}

export function getDownloadUrl(jobId, kind) {
  const routes = { video: "video", csv: "csv", json: "json" };
  if (!routes[kind]) throw new Error("Unsupported download type");
  return `${API_BASE_URL}/api/jobs/${encodeURIComponent(jobId)}/${routes[kind]}`;
}

export async function deleteJob(jobId) {
  return request(`/api/jobs/${encodeURIComponent(jobId)}`, { method: "DELETE" });
}


/**
 * PragyanAI - Video People Counting
 * API Service
 *
 * Backend: FastAPI
 * Frontend: React + Vite
 *
 * Configure the backend URL in frontend/.env:
 * VITE_API_BASE_URL=https://YOUR-RENDER-BACKEND.onrender.com
 */

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"
).replace(/\/+$/, "");

const API_PREFIX = "/api";

const DEFAULT_TIMEOUT = 15000;

/**
 * Build API endpoint URL.
 */
const buildUrl = (endpoint) => {
  const normalizedEndpoint = endpoint.startsWith("/")
    ? endpoint
    : `/${endpoint}`;

  return `${API_BASE_URL}${API_PREFIX}${normalizedEndpoint}`;
};

/**
 * Common fetch handler with timeout and error handling.
 */
const apiRequest = async (endpoint, options = {}) => {
  const controller = new AbortController();

  const timeoutMs =
    options.timeout === 0
      ? 0
      : (options.timeout ?? DEFAULT_TIMEOUT);

  const timeout =
    timeoutMs > 0
      ? setTimeout(() => controller.abort(), timeoutMs)
      : null;

  try {
    const response = await fetch(buildUrl(endpoint), {
      ...options,
      signal: controller.signal,
    });

    const contentType = response.headers.get("content-type") || "";

    let responseData;

    if (contentType.includes("application/json")) {
      responseData = await response.json();
    } else {
      responseData = await response.text();
    }

    if (!response.ok) {
      const errorMessage =
        responseData?.detail ||
        responseData?.message ||
        responseData ||
        `API request failed with status ${response.status}`;

      throw new Error(
        typeof errorMessage === "string"
          ? errorMessage
          : JSON.stringify(errorMessage)
      );
    }

    return responseData;
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("Request timed out. Please try again.");
    }

    if (error instanceof TypeError) {
      throw new Error(
        "Unable to connect to the backend. Please check the API URL and server status."
      );
    }

    throw error;
  } finally {
    if (timeout) clearTimeout(timeout);
  }
};

/**
 * 1. Backend Health Check
 *
 * Expected endpoint:
 * GET /api/health
 */
export const healthCheck = async () => {
  return await apiRequest("/health", {
    method: "GET",
  });
};

/**
 * 2. Create Video Processing Job
 *
 * Expected endpoint:
 * POST /api/jobs
 *
 * Form fields:
 * - file
 * - confidence
 * - frame_interval
 */
export const createVideoJob = async (
  file,
  confidence = 0.35,
  frameInterval = 1
) => {
  if (!file) {
    throw new Error("Please select a video file.");
  }

  const formData = new FormData();

  formData.append("file", file);
  formData.append("confidence", String(confidence));
  formData.append("frame_interval", String(frameInterval));

  return await apiRequest("/jobs", {
    method: "POST",
    body: formData,

    // Upload is the only long HTTP request.
    // Video analysis runs asynchronously and is monitored
    // through the EventSource stream.
    timeout: 0,
  });
};

/**
 * 3. Subscribe to live job updates using Server-Sent Events.
 *
 * The browser automatically reconnects if the network
 * briefly disconnects.
 */
export const subscribeJobEvents = (
  jobId,
  onUpdate,
  onClosed
) => {
  if (!jobId) {
    throw new Error("Job ID is required.");
  }

  const source = new EventSource(
    buildUrl(`/jobs/${encodeURIComponent(jobId)}/events`)
  );

  source.addEventListener("progress", (event) => {
    try {
      const payload = JSON.parse(event.data);

      onUpdate?.(payload);

      if (
        ["completed", "failed", "cancelled"].includes(
          payload.status
        )
      ) {
        source.close();
      }
    } catch (error) {
      console.error("Could not parse live job event:", error);
    }
  });

  source.onerror = () => {
    // CONNECTING means EventSource is retrying automatically.
    // Report a terminal failure only when the browser closes
    // the stream.
    if (source.readyState === EventSource.CLOSED) {
      onClosed?.(
        new Error("Live progress connection closed.")
      );
    }
  };

  return source;
};

/**
 * 4. Get Video Processing Job Status (snapshot fallback)
 *
 * Expected endpoint:
 * GET /api/jobs/{jobId}
 */
export const getJobStatus = async (jobId) => {
  if (!jobId) {
    throw new Error("Job ID is required.");
  }

  return await apiRequest(
    `/jobs/${encodeURIComponent(jobId)}`,
    {
      method: "GET",
    }
  );
};

/**
 * 5. Get Job Analytics
 *
 * Expected endpoint:
 * GET /api/jobs/{jobId}/analytics
 */
export const getJobAnalytics = async (jobId) => {
  if (!jobId) {
    throw new Error("Job ID is required.");
  }

  return await apiRequest(
    `/jobs/${encodeURIComponent(jobId)}/analytics`,
    {
      method: "GET",
    }
  );
};

/**
 * 6. Get an output download URL.
 *
 * Backend routes:
 * GET /api/jobs/{jobId}/video
 * GET /api/jobs/{jobId}/csv
 * GET /api/jobs/{jobId}/json
 */
export const getDownloadUrl = (
  jobId,
  outputType = "video"
) => {
  if (!jobId) {
    throw new Error("Job ID is required.");
  }

  const allowedTypes = new Set([
    "video",
    "csv",
    "json",
  ]);

  if (!allowedTypes.has(outputType)) {
    throw new Error(
      `Unsupported output type: ${outputType}. Use video, csv or json.`
    );
  }

  return buildUrl(
    `/jobs/${encodeURIComponent(jobId)}/${outputType}`
  );
};

/**
 * 7. Download Processed Video
 */
export const downloadProcessedVideo = async (
  jobId,
  filename = "pragyanai_people_counted.mp4"
) => {
  if (!jobId) {
    throw new Error("Job ID is required.");
  }

  const response = await fetch(getDownloadUrl(jobId));

  if (!response.ok) {
    throw new Error(
      "Unable to download the processed video."
    );
  }

  const blob = await response.blob();

  const objectUrl = window.URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;

  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  window.URL.revokeObjectURL(objectUrl);
};

/**
 * 8. Get Backend Model Information
 *
 * Expected endpoint:
 * GET /api/model-info
 */
export const getModelInfo = async () => {
  return await apiRequest("/model-info", {
    method: "GET",
  });
};

/**
 * 9. Cancel a Processing Job
 *
 * Optional endpoint:
 * DELETE /api/jobs/{jobId}
 *
 * Implement this route in FastAPI before using this function.
 */
export const cancelVideoJob = async (jobId) => {
  if (!jobId) {
    throw new Error("Job ID is required.");
  }

  return await apiRequest(
    `/jobs/${encodeURIComponent(jobId)}`,
    {
      method: "DELETE",
    }
  );
};

/**
 * 10. Get API Base URL
 */
export const getApiBaseUrl = () => API_BASE_URL;

/**
 * 11. Default API Service
 */
const api = {
  healthCheck,
  createVideoJob,
  subscribeJobEvents,
  getJobStatus,
  getJobAnalytics,
  getDownloadUrl,
  downloadProcessedVideo,
  getModelInfo,
  cancelVideoJob,
  getApiBaseUrl,
};

export default api;

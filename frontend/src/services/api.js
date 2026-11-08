
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

const DEFAULT_TIMEOUT = 30000;

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

  const timeout = setTimeout(() => {
    controller.abort();
  }, options.timeout || DEFAULT_TIMEOUT);

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
    clearTimeout(timeout);
  }
};

/**
 * 1. Backend Health Check
 *
 * Expected endpoint:
 * GET /api/health
 *
 * Adjust this endpoint if your backend health router
 * exposes a different route.
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
    timeout: 120000,
  });
};

/**
 * 3. Get Video Processing Job Status
 *
 * Expected endpoint:
 * GET /api/jobs/{jobId}
 */
export const getJobStatus = async (jobId) => {
  if (!jobId) {
    throw new Error("Job ID is required.");
  }

  return await apiRequest(`/jobs/${encodeURIComponent(jobId)}`, {
    method: "GET",
  });
};

/**
 * 4. Get Job Analytics
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
 * 5. Get Processed Video Download URL
 *
 * Expected endpoint:
 * GET /api/downloads/{jobId}
 *
 * Returns a URL that can be used by the browser.
 */
export const getDownloadUrl = (jobId) => {
  if (!jobId) {
    throw new Error("Job ID is required.");
  }

  return buildUrl(`/downloads/${encodeURIComponent(jobId)}`);
};

/**
 * 6. Download Processed Video
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
    throw new Error("Unable to download the processed video.");
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
 * 7. Get Backend Model Information
 *
 * Expected endpoint:
 * GET /api/model-info
 *
 * Adjust this route if your backend uses another endpoint.
 */
export const getModelInfo = async () => {
  return await apiRequest("/model-info", {
    method: "GET",
  });
};

/**
 * 8. Cancel a Processing Job
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

  return await apiRequest(`/jobs/${encodeURIComponent(jobId)}`, {
    method: "DELETE",
  });
};

/**
 * 9. Get API Base URL
 */
export const getApiBaseUrl = () => API_BASE_URL;

/**
 * 10. Default API Service
 */
const api = {
  healthCheck,
  createVideoJob,
  getJobStatus,
  getJobAnalytics,
  getDownloadUrl,
  downloadProcessedVideo,
  getModelInfo,
  cancelVideoJob,
  getApiBaseUrl,
};

export default api;

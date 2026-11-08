
/**
 * PragyanAI - Video People Counting
 * API Service
 *
 * Backend: FastAPI
 * Frontend: React + Vite
 *
 * Configure the backend URL in frontend/.env:
 * VITE_API_BASE_URL=https://pragyanai-video-people-counting-pytorch.onrender.com
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

    const contentType =
      response.headers.get("content-type") || "";

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
    if (timeout) {
      clearTimeout(timeout);
    }
  }
};

/**
 * 1. Backend Health Check
 *
 * Expected endpoint:
 * GET /health
 *
 * The Render health check uses the root /health route.
 */
export const healthCheck = async () => {
  const controller = new AbortController();

  const timeout = setTimeout(
    () => controller.abort(),
    DEFAULT_TIMEOUT
  );

  try {
    const response = await fetch(
      `${API_BASE_URL}/health`,
      {
        method: "GET",
        signal: controller.signal,
      }
    );

    if (!response.ok) {
      throw new Error(
        `Backend health check failed: HTTP ${response.status}`
      );
    }

    return await response.json();
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("Backend health check timed out.");
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
  frameInterval = 3
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

    // Upload can take longer than an ordinary API request.
    // Video processing runs asynchronously in the backend.
    // Progress is received through SSE.
    timeout: 0,
  });
};

/**
 * 3. Subscribe to Live Job Updates Using SSE
 *
 * The browser automatically reconnects when the network
 * briefly disconnects.
 *
 * Parameters:
 * jobId          - Processing job ID
 * onUpdate       - Receives job progress snapshots
 * onClosed       - Called when the connection permanently closes
 * onReconnecting - Called while EventSource is reconnecting
 *
 * Returns:
 * A cleanup function to close the SSE connection.
 */
export const subscribeJobEvents = (
  jobId,
  onUpdate,
  onClosed,
  onReconnecting
) => {
  if (!jobId) {
    throw new Error("Job ID is required.");
  }

  const source = new EventSource(
    buildUrl(
      `/jobs/${encodeURIComponent(jobId)}/events`
    )
  );

  let intentionallyClosed = false;
  let statusCheckInProgress = false;

  source.onopen = () => {
    console.info(
      "SSE progress connection established."
    );
  };

  source.addEventListener("progress", (event) => {
    try {
      const payload = JSON.parse(event.data);

      onUpdate?.(payload);

      // Close the connection only after a terminal status.
      if (
        ["completed", "failed", "cancelled"].includes(
          payload.status
        )
      ) {
        intentionallyClosed = true;
        source.close();
      }
    } catch (error) {
      console.error(
        "Could not parse live job event:",
        error
      );
    }
  });

  source.onerror = async () => {
    if (intentionallyClosed) {
      return;
    }

    if (source.readyState === EventSource.CONNECTING) {
      console.warn(
        "SSE disconnected. Browser will reconnect automatically."
      );

      onReconnecting?.();

      return;
    }

    if (
      source.readyState === EventSource.CLOSED &&
      !statusCheckInProgress
    ) {
      statusCheckInProgress = true;

      console.error(
        "SSE connection permanently closed. Checking job status."
      );

      try {
        const latest = await getJobStatus(jobId);

        onUpdate?.(latest);

        if (
          ["completed", "failed", "cancelled"].includes(
            latest.status
          )
        ) {
          intentionallyClosed = true;
          return;
        }

        onClosed?.(
          new Error(
            "The live progress stream closed. The job status was checked, but the job may still be active."
          )
        );
      } catch (error) {
        onClosed?.(error);
      } finally {
        statusCheckInProgress = false;
      }
    }
  };

  // Return cleanup function for React useEffect.
  return () => {
    intentionallyClosed = true;
    source.close();

    console.info(
      "SSE progress connection closed by frontend."
    );
  };
};

/**
 * 4. Get Video Processing Job Status
 *
 * Snapshot fallback endpoint:
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
 * 6. Get Download URL
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

  const response = await fetch(
    getDownloadUrl(jobId, "video")
  );

  if (!response.ok) {
    throw new Error(
      "Unable to download the processed video."
    );
  }

  const blob = await response.blob();

  const objectUrl =
    window.URL.createObjectURL(blob);

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
 * Optional backend endpoint:
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

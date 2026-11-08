
/**
 * PragyanAI - Video People Counting
 * Utility functions for formatting application data.
 */

// --------------------------------------------------
// 1. FILE SIZE FORMATTER
// --------------------------------------------------

export function formatBytes(bytes, decimals = 2) {
  if (bytes === null || bytes === undefined || bytes < 0) {
    return "0 Bytes";
  }

  if (bytes === 0) {
    return "0 Bytes";
  }

  const k = 1024;

  const sizes = [
    "Bytes",
    "KB",
    "MB",
    "GB",
    "TB"
  ];

  const dm = Math.max(0, decimals);

  const i = Math.min(
    Math.floor(Math.log(bytes) / Math.log(k)),
    sizes.length - 1
  );

  return (
    parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) +
    " " +
    sizes[i]
  );
}


// --------------------------------------------------
// 2. VIDEO DURATION FORMATTER
// --------------------------------------------------

export function formatDuration(seconds) {
  if (
    seconds === null ||
    seconds === undefined ||
    !Number.isFinite(Number(seconds)) ||
    Number(seconds) < 0
  ) {
    return "00:00";
  }

  const totalSeconds = Math.floor(Number(seconds));

  const hours = Math.floor(totalSeconds / 3600);

  const minutes = Math.floor(
    (totalSeconds % 3600) / 60
  );

  const remainingSeconds = totalSeconds % 60;

  const pad = (value) =>
    String(value).padStart(2, "0");

  if (hours > 0) {
    return (
      `${pad(hours)}:` +
      `${pad(minutes)}:` +
      `${pad(remainingSeconds)}`
    );
  }

  return (
    `${pad(minutes)}:` +
    `${pad(remainingSeconds)}`
  );
}


// --------------------------------------------------
// 3. PROCESSING TIME FORMATTER
// --------------------------------------------------

export function formatTime(seconds) {
  if (
    seconds === null ||
    seconds === undefined ||
    !Number.isFinite(Number(seconds)) ||
    Number(seconds) < 0
  ) {
    return "0 sec";
  }

  const value = Number(seconds);

  if (value < 60) {
    return `${value.toFixed(1)} sec`;
  }

  const minutes = Math.floor(value / 60);

  const remainingSeconds = Math.floor(value % 60);

  if (minutes < 60) {
    return `${minutes}m ${remainingSeconds}s`;
  }

  const hours = Math.floor(minutes / 60);

  const remainingMinutes = minutes % 60;

  return `${hours}h ${remainingMinutes}m`;
}


// --------------------------------------------------
// 4. NUMBER FORMATTER
// --------------------------------------------------

export function formatNumber(value, decimals = 0) {
  if (
    value === null ||
    value === undefined ||
    !Number.isFinite(Number(value))
  ) {
    return "0";
  }

  return Number(value).toLocaleString("en-IN", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  });
}


// --------------------------------------------------
// 5. PERCENTAGE FORMATTER
// --------------------------------------------------

export function formatPercent(value, decimals = 1) {
  if (
    value === null ||
    value === undefined ||
    !Number.isFinite(Number(value))
  ) {
    return "0%";
  }

  return `${Number(value).toFixed(decimals)}%`;
}


// --------------------------------------------------
// 6. CONFIDENCE SCORE FORMATTER
// --------------------------------------------------

export function formatConfidence(value, decimals = 2) {
  if (
    value === null ||
    value === undefined ||
    !Number.isFinite(Number(value))
  ) {
    return "0.00";
  }

  const score = Number(value);

  // Convert probability to percentage if between 0 and 1
  if (score >= 0 && score <= 1) {
    return `${(score * 100).toFixed(decimals)}%`;
  }

  return `${score.toFixed(decimals)}%`;
}


// --------------------------------------------------
// 7. FRAME RATE FORMATTER
// --------------------------------------------------

export function formatFPS(value) {
  if (
    value === null ||
    value === undefined ||
    !Number.isFinite(Number(value))
  ) {
    return "0 FPS";
  }

  return `${Number(value).toFixed(1)} FPS`;
}


// --------------------------------------------------
// 8. VIDEO RESOLUTION FORMATTER
// --------------------------------------------------

export function formatResolution(width, height) {
  if (!width || !height) {
    return "Unknown";
  }

  return `${width} × ${height}`;
}


// --------------------------------------------------
// 9. DATE FORMATTER
// --------------------------------------------------

export function formatDate(date) {
  if (!date) {
    return "N/A";
  }

  const parsedDate = new Date(date);

  if (Number.isNaN(parsedDate.getTime())) {
    return "N/A";
  }

  return parsedDate.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric"
  });
}


// --------------------------------------------------
// 10. DATE AND TIME FORMATTER
// --------------------------------------------------

export function formatDateTime(date) {
  if (!date) {
    return "N/A";
  }

  const parsedDate = new Date(date);

  if (Number.isNaN(parsedDate.getTime())) {
    return "N/A";
  }

  return parsedDate.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  });
}


// --------------------------------------------------
// 11. TIME AGO FORMATTER
// --------------------------------------------------

export function formatTimeAgo(date) {
  if (!date) {
    return "N/A";
  }

  const parsedDate = new Date(date);

  if (Number.isNaN(parsedDate.getTime())) {
    return "N/A";
  }

  const seconds = Math.floor(
    (Date.now() - parsedDate.getTime()) / 1000
  );

  if (seconds < 0) {
    return "Just now";
  }

  if (seconds < 60) {
    return "Just now";
  }

  const minutes = Math.floor(seconds / 60);

  if (minutes < 60) {
    return `${minutes} min ago`;
  }

  const hours = Math.floor(minutes / 60);

  if (hours < 24) {
    return `${hours} hours ago`;
  }

  const days = Math.floor(hours / 24);

  if (days < 30) {
    return `${days} days ago`;
  }

  return formatDate(parsedDate);
}


// --------------------------------------------------
// 12. STATUS FORMATTER
// --------------------------------------------------

export function formatStatus(status) {
  if (!status) {
    return "Unknown";
  }

  return String(status)
    .replace(/[_-]/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}


// --------------------------------------------------
// 13. JOB STATUS COLOR
// --------------------------------------------------

export function getStatusColor(status) {
  const normalized = String(status || "").toLowerCase();

  const colors = {
    queued: "warning",
    pending: "warning",
    processing: "info",
    running: "info",
    completed: "success",
    failed: "danger",
    cancelled: "secondary"
  };

  return colors[normalized] || "secondary";
}


// --------------------------------------------------
// 14. CSV FILE NAME FORMATTER
// --------------------------------------------------

export function formatFileName(name) {
  if (!name) {
    return "video";
  }

  return String(name)
    .replace(/\.[^/.]+$/, "")
    .replace(/[^a-zA-Z0-9_-]/g, "_")
    .slice(0, 100);
}


// --------------------------------------------------
// 15. GENERATE DOWNLOAD FILE NAME
// --------------------------------------------------

export function generateDownloadName(
  originalName,
  extension = "csv"
) {
  const baseName = formatFileName(originalName);

  return `${baseName}_people_counting.${extension}`;
}


// --------------------------------------------------
// 16. SAFE NUMERIC CONVERSION
// --------------------------------------------------

export function toNumber(value, fallback = 0) {
  const number = Number(value);

  return Number.isFinite(number)
    ? number
    : fallback;
}


// --------------------------------------------------
// 17. CLAMP NUMERIC VALUE
// --------------------------------------------------

export function clamp(value, min, max) {
  const number = toNumber(value, min);

  return Math.min(
    Math.max(number, min),
    max
  );
}


// --------------------------------------------------
// 18. PROCESSING PROGRESS FORMATTER
// --------------------------------------------------

export function formatProgress(progress) {
  const value = clamp(progress, 0, 100);

  return `${Math.round(value)}%`;
}


// --------------------------------------------------
// 19. FRAME COUNT FORMATTER
// --------------------------------------------------

export function formatFrameCount(value) {
  return formatNumber(value, 0);
}


// --------------------------------------------------
// 20. UNIQUE PEOPLE COUNT FORMATTER
// --------------------------------------------------

export function formatPeopleCount(value) {
  const count = toNumber(value, 0);

  return `${formatNumber(count)} ${
    count === 1 ? "Person" : "People"
  }`;
}


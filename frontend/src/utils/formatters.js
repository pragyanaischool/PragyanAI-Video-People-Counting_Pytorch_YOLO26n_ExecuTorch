export function formatDuration(seconds = 0) {
  const value = Math.max(0, Math.floor(Number(seconds) || 0));
  const minutes = Math.floor(value / 60);
  const remainder = value % 60;
  return minutes ? `${minutes}m ${remainder}s` : `${remainder}s`;
}

export function formatBytes(bytes = 0) {
  const value = Number(bytes) || 0;
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatPercent(value = 0) {
  return `${Math.max(0, Math.min(100, Number(value) || 0)).toFixed(1)}%`;
}

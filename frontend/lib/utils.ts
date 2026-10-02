import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format an ISO timestamp for display. Returns UNKNOWN for missing/invalid
 * input rather than an invented date, so the UI never implies evidence
 * that was not recorded.
 */
export function formatDate(value?: string | null): string {
  if (!value) return "UNKNOWN";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "UNKNOWN";
  return parsed.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Format a duration expressed in seconds. UNKNOWN when not recorded.
 */
export function formatDuration(seconds?: number | null): string {
  if (seconds === null || seconds === undefined || Number.isNaN(seconds)) return "UNKNOWN";
  if (seconds < 0) return "UNKNOWN";
  if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`;
  if (seconds < 60) return `${seconds.toFixed(2)}s`;
  const minutes = Math.floor(seconds / 60);
  const remaining = seconds % 60;
  if (minutes < 60) return `${minutes}m ${remaining.toFixed(0)}s`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
}

/**
 * Truncate text to `length` characters, appending an ellipsis when cut.
 */
export function truncate(text: unknown, length = 80): string {
  if (text === null || text === undefined) return "UNKNOWN";
  const str = String(text);
  if (str.length <= length) return str;
  return `${str.slice(0, Math.max(0, length - 1))}…`;
}

/**
 * Tailwind classes for a 0-100 confidence/percentage value.
 */
export function getConfidenceColor(confidence?: number | null): string {
  if (confidence === null || confidence === undefined || Number.isNaN(confidence)) {
    return "bg-gray-700 text-gray-300";
  }
  if (confidence >= 90) return "bg-green-900/30 text-green-300";
  if (confidence >= 70) return "bg-yellow-900/30 text-yellow-300";
  if (confidence >= 40) return "bg-orange-900/30 text-orange-300";
  return "bg-red-900/30 text-red-300";
}
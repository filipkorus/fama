export function formatTimeAgo(dateString?: string | null): string {
  if (!dateString) return '';

  let normalizedDate = dateString;
  if (!dateString.endsWith('Z') && !/[+-]\d{2}:?\d{2}/.test(dateString)) {
    normalizedDate = `${dateString}Z`;
  }

  const date = new Date(normalizedDate);
  const now = new Date();

  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (seconds < 0) return "now";

  let interval = seconds / 31536000;
  if (interval > 1) return Math.floor(interval) + "y";

  interval = seconds / 2592000;
  if (interval > 1) return Math.floor(interval) + "mo";

  interval = seconds / 86400;
  if (interval > 1) return Math.floor(interval) + "d";

  interval = seconds / 3600;
  if (interval > 1) return Math.floor(interval) + "h";

  interval = seconds / 60;
  if (interval > 1) return Math.floor(interval) + "m";

  return "now";
}

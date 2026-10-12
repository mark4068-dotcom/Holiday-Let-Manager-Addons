const parseTime = value => {
  const time = Date.parse(value || "");
  return Number.isFinite(time) ? time : null;
};

export function isStale(state, payload, options = {}, now = Date.now()) {
  const intervalMs = Math.max(60_000, Number(options.refresh_minutes || 5) * 60_000);
  const maxAgeMs = Math.max(intervalMs * 2, 15 * 60_000);
  const updatedAt = parseTime(payload?.updated_at);
  const nextUpdate = parseTime(state?.next_update_at);
  const lastAttempt = parseTime(state?.last_attempt_at);

  return Boolean(
    state?.error ||
    state?.source_errors?.length ||
    !updatedAt ||
    now - updatedAt > maxAgeMs ||
    (state?.running && nextUpdate !== null && nextUpdate <= now) ||
    (state?.running && lastAttempt !== null && now - lastAttempt > maxAgeMs),
  );
}

export function collectionTimeoutMs(options = {}) {
  const intervalMs = Math.max(60_000, Number(options.refresh_minutes || 5) * 60_000);
  return Math.max(120_000, intervalMs);
}

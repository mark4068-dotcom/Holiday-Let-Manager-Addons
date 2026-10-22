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
    state?.recovery_required ||
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

// A deadline cannot cancel a stuck browser promise. Signal the existing
// Supervisor watchdog so it can restart the app and terminate its browser.
export function withCollectionTimeout(promise, timeoutMs, onTimeout = () => {}) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      onTimeout();
      reject(new Error(`Collection timed out after ${Math.round(timeoutMs / 1000)} seconds`));
    }, timeoutMs);
    promise.then(
      value => { clearTimeout(timer); resolve(value); },
      error => { clearTimeout(timer); reject(error); },
    );
  });
}

export function collectorHealth(state, payload, options = {}, now = Date.now()) {
  return {
    statusCode: state.recovery_required ? 503 : 200,
    payload: {
      ok: Boolean(payload.updated_at),
      stale: isStale(state, payload, options, now),
      ...state,
      service_count: payload.services.length,
    },
  };
}

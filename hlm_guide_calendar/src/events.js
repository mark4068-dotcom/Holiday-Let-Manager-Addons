import { addDays } from "./calendar.js";

export function dateInTimezone(date = new Date(), timezone = "Europe/London") {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date);
  const values = Object.fromEntries(parts.map(({ type, value }) => [type, value]));
  return `${values.year}-${values.month}-${values.day}`;
}

export function upcomingEvents(events, {
  horizonDays = 10,
  now = new Date(),
  timezone = "Europe/London",
} = {}) {
  const today = dateInTimezone(now, timezone);
  const lastStartDate = addDays(today, Number(horizonDays));

  return events.filter((event) => {
    if (!event?.start || !event?.end) return false;
    // Event end dates are exclusive. Retain an event already in progress and
    // any event beginning on or before the inclusive horizon date.
    return event.end > today && event.start <= lastStartDate;
  });
}

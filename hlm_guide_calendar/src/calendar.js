import crypto from "node:crypto";

const escapeText = (value = "") => String(value)
  .replaceAll("\\", "\\\\")
  .replaceAll("\n", "\\n")
  .replaceAll(",", "\\,")
  .replaceAll(";", "\\;");

const foldLine = (line) => {
  const chunks = [];
  let remaining = line;
  while (Buffer.byteLength(remaining, "utf8") > 73) {
    let cut = 73;
    while (Buffer.byteLength(remaining.slice(0, cut), "utf8") > 73) cut -= 1;
    chunks.push(remaining.slice(0, cut));
    remaining = ` ${remaining.slice(cut)}`;
  }
  chunks.push(remaining);
  return chunks.join("\r\n");
};

const compactDate = (isoDate) => isoDate.replaceAll("-", "");

export function stableUid(event) {
  const material = [event.summary, event.start, event.location]
    .map((part) => String(part || "").trim().toLowerCase())
    .join("|");
  return `${crypto.createHash("sha256").update(material).digest("hex").slice(0, 20)}@holiday-guide.local`;
}

export function eventsToIcs(events, generatedAt = new Date()) {
  const stamp = generatedAt.toISOString().replace(/[-:]/g, "").replace(/\.\d{3}Z$/, "Z");
  const lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Holiday Let Manager//Guest Events//EN",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    "X-WR-CALNAME:Local events",
    "X-WR-TIMEZONE:Europe/London",
  ];

  for (const event of events) {
    lines.push(
      "BEGIN:VEVENT",
      `UID:${event.uid || stableUid(event)}`,
      `DTSTAMP:${stamp}`,
      `DTSTART;VALUE=DATE:${compactDate(event.start)}`,
      `DTEND;VALUE=DATE:${compactDate(event.end)}`,
      `SUMMARY:${escapeText(event.summary)}`,
      `LOCATION:${escapeText(event.location)}`,
      `DESCRIPTION:${escapeText(event.description)}`,
    );
    if (event.url) lines.push(`URL:${escapeText(event.url)}`);
    lines.push("END:VEVENT");
  }
  lines.push("END:VCALENDAR");
  return `${lines.map(foldLine).join("\r\n")}\r\n`;
}

export function addDays(isoDate, days) {
  const date = new Date(`${isoDate}T12:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

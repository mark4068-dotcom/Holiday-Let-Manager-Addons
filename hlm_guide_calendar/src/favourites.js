const tidy = (value) => String(value || "").replace(/\s+/g, " ").trim();

const ignoredFavouriteDetail = (line) => (
  /^(open now|closed|open|view in map|more\s|home|explore|property|about|£+|★+|\d+\s+miles? away)$/i.test(line)
  || /^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday):/i.test(line)
  || /^(?:⏰|📞)/u.test(line)
);

export function favouriteFromText(lines, cardLabel, { mapsUrl = "", sourceUrl = "" } = {}) {
  const cleanLines = lines.map(tidy).filter(Boolean);
  const normalizedLabel = tidy(cardLabel).toLowerCase();
  const titleIndex = cleanLines.findIndex((line) => line.toLowerCase() === normalizedLabel);
  if (titleIndex < 0) return null;

  const remaining = cleanLines.slice(titleIndex + 1);
  const relatedIndex = remaining.findIndex((line) => /^more\s+/i.test(line));
  const details = relatedIndex >= 0 ? remaining.slice(0, relatedIndex) : remaining;
  const hours = details.filter((line) => /^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday):/i.test(line));
  const address = details.find((line) => /\bPO\d{1,2}\s*\d[A-Z]{2}\b/i.test(line)) || "";
  const description = details.find((line) => (
    line !== address
    && line.length > 20
    && !ignoredFavouriteDetail(line)
    && !/\bPO\d{1,2}\s*\d[A-Z]{2}\b/i.test(line)
  )) || "";

  return {
    name: cleanLines[titleIndex],
    description,
    address,
    opening_hours: hours,
    maps_url: mapsUrl,
    source_url: sourceUrl,
  };
}

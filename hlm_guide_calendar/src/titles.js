const normalizeTitle = (value) => String(value || "")
  .replace(/\s+/g, " ")
  .trim()
  .toLocaleLowerCase("en-GB")
  .replace(/[^a-z0-9]+/g, " ")
  .trim();

export function titlesMatch(selectedTitle, detailTitle) {
  const selected = normalizeTitle(selectedTitle);
  const detail = normalizeTitle(detailTitle);
  return Boolean(selected && detail && (
    selected === detail
    || selected.startsWith(detail)
    || detail.startsWith(selected)
  ));
}

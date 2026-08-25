const escapeHtml = (value = "") => String(value).replace(/[&<>"']/g, (character) => ({
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
})[character]);

const safeUrl = (value = "") => {
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) ? escapeHtml(url.href) : "";
  } catch {
    return "";
  }
};

const formatDateRange = (start, end) => {
  const startDate = new Date(`${start}T12:00:00Z`);
  const endDate = new Date(`${end}T12:00:00Z`);
  endDate.setUTCDate(endDate.getUTCDate() - 1);
  const date = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
  if (startDate.toISOString().slice(0, 10) === endDate.toISOString().slice(0, 10)) return date.format(startDate);
  const compact = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });
  return `${compact.format(startDate)} – ${date.format(endDate)}`;
};

const eventCard = (event) => {
  const href = safeUrl(event.url);
  const link = href ? `<a class="details" href="${href}" target="_blank" rel="noopener">View event <span aria-hidden="true">→</span></a>` : "";
  return `<article class="event-card">
    <div class="date-badge">${escapeHtml(formatDateRange(event.start, event.end))}</div>
    <h3>${escapeHtml(event.summary)}</h3>
    <p class="location"><span aria-hidden="true">⌖</span> ${escapeHtml(event.location || "Isle of Wight")}</p>
    <p class="description">${escapeHtml(event.description || "More information is available in the digital guide.")}</p>
    ${link}
  </article>`;
};

const favouriteCard = (place, index) => {
  const href = safeUrl(place.source_url);
  const maps = safeUrl(place.maps_url);
  const initials = String(place.name || "Place").split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
  const links = [
    maps ? `<a class="pill" href="${maps}" target="_blank" rel="noopener">Directions</a>` : "",
    href ? `<a class="pill secondary" href="${href}" target="_blank" rel="noopener">Guide details</a>` : "",
  ].join("");
  return `<article class="place-card" aria-label="${escapeHtml(place.name)}">
    <div class="place-hero shade-${index % 6}"><span>${escapeHtml(initials)}</span></div>
    <div class="place-content">
      <h3>${escapeHtml(place.name)}</h3>
      <p class="location">${escapeHtml(place.address || "Isle of Wight")}</p>
      <p class="description">${escapeHtml(place.description || "One of our favourite local places.")}</p>
      <div class="actions">${links}</div>
    </div>
  </article>`;
};

export function guestPage({ events = [], favourites = [], updatedAt = null } = {}) {
  const eventCards = events.length ? events.map(eventCard).join("") : `<p class="empty">Local events are being updated. Please check again shortly.</p>`;
  const placeCards = favourites.length ? favourites.map(favouriteCard).join("") : `<p class="empty">Favourite places are being updated. Please check again shortly.</p>`;
  const updated = updatedAt ? new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short", timeZone: "Europe/London" }).format(new Date(updatedAt)) : "pending";
  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Local Events & Favourite Places</title>
<style>
:root{color-scheme:light;--ink:#17324d;--muted:#60758a;--sea:#087f8c;--foam:#edf8f7;--sand:#fffaf0;--line:#dce7ec;--shadow:0 10px 28px rgba(28,61,82,.12)}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(180deg,#f4fbfc 0,#fff 24rem);color:var(--ink);font:16px/1.5 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
main{max-width:1500px;margin:auto;padding:clamp(1rem,2.4vw,2.25rem)}.eyebrow{margin:0;color:var(--sea);font-size:.82rem;font-weight:800;letter-spacing:.13em;text-transform:uppercase}h1{margin:.2rem 0 .3rem;font-size:clamp(1.9rem,4vw,3.4rem);line-height:1.05}h2{margin:2.2rem 0 .8rem;font-size:clamp(1.4rem,2.4vw,2rem)}h3{margin:.35rem 0;font-size:1.25rem;line-height:1.25}.intro,.location{color:var(--muted)}
.events{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr));gap:1rem}.event-card,.place-card{background:#fff;border:1px solid var(--line);border-radius:20px;box-shadow:var(--shadow);overflow:hidden}.event-card{display:flex;min-height:270px;flex-direction:column;padding:1.25rem}.date-badge{align-self:flex-start;border-radius:999px;background:var(--foam);color:#086a73;padding:.35rem .7rem;font-size:.83rem;font-weight:750}.description{display:-webkit-box;overflow:hidden;-webkit-box-orient:vertical;-webkit-line-clamp:4;color:#40566a}.details{margin-top:auto;color:var(--sea);font-weight:750;text-decoration:none}
.carousel-wrap{position:relative}.carousel{display:grid;grid-auto-flow:column;grid-auto-columns:min(84vw,350px);gap:1rem;overflow-x:auto;scroll-snap-type:x mandatory;scroll-behavior:smooth;padding:.25rem .15rem 1.3rem;scrollbar-width:thin;scrollbar-color:#9dc5ca transparent}.place-card{scroll-snap-align:start}.place-hero{display:grid;height:118px;place-items:center;background:linear-gradient(135deg,#168a94,#72c8bd)}.place-hero span{display:grid;width:66px;height:66px;place-items:center;border:2px solid rgba(255,255,255,.7);border-radius:50%;background:rgba(255,255,255,.18);color:#fff;font-size:1.45rem;font-weight:800}.shade-1{background:linear-gradient(135deg,#ee8c5b,#f6c36a)}.shade-2{background:linear-gradient(135deg,#4d7198,#8bb1c8)}.shade-3{background:linear-gradient(135deg,#7e6a9f,#c39ac8)}.shade-4{background:linear-gradient(135deg,#528b63,#9bc17b)}.shade-5{background:linear-gradient(135deg,#b2675e,#e5a98e)}.place-content{display:flex;min-height:275px;flex-direction:column;padding:1rem 1.1rem}.place-content .location{min-height:2.8em;margin:.2rem 0;font-size:.88rem}.actions{display:flex;flex-wrap:wrap;gap:.5rem;margin-top:auto}.pill{border-radius:999px;background:var(--sea);color:#fff;padding:.5rem .8rem;font-size:.86rem;font-weight:700;text-decoration:none}.pill.secondary{background:#e9f3f4;color:#17606a}
.carousel-controls{display:flex;gap:.6rem;position:absolute;right:.2rem;top:-3.15rem}.carousel-controls button{width:42px;height:42px;border:1px solid var(--line);border-radius:50%;background:#fff;color:var(--ink);box-shadow:0 4px 14px rgba(28,61,82,.12);font-size:1.25rem;cursor:pointer}.empty{padding:1rem;border-radius:14px;background:var(--sand)}footer{margin-top:1rem;color:#8293a2;font-size:.78rem;text-align:right}
@media(max-width:600px){main{padding:.9rem}.carousel-controls{display:none}.event-card{min-height:240px}.place-content{min-height:260px}}
@media(prefers-reduced-motion:reduce){.carousel{scroll-behavior:auto}}
</style></head><body><main>
<header><p class="eyebrow">Crossjack guest guide</p><h1>Local events & favourite places</h1><p class="intro">A few ideas to help you make the most of your stay on the Isle of Wight.</p></header>
<section aria-labelledby="events-heading"><h2 id="events-heading">What’s on</h2><div class="events">${eventCards}</div></section>
<section aria-labelledby="places-heading"><h2 id="places-heading">Our favourite places</h2><div class="carousel-wrap"><div class="carousel-controls"><button type="button" data-direction="-1" aria-label="Previous places">‹</button><button type="button" data-direction="1" aria-label="Next places">›</button></div><div class="carousel" id="places-carousel" tabindex="0">${placeCards}</div></div></section>
<footer>Guide information last updated ${escapeHtml(updated)}</footer>
</main><script>
const carousel=document.getElementById("places-carousel");
document.querySelectorAll("[data-direction]").forEach(button=>button.addEventListener("click",()=>carousel.scrollBy({left:Number(button.dataset.direction)*Math.min(carousel.clientWidth*.9,720),behavior:"smooth"})));
</script></body></html>`;
}

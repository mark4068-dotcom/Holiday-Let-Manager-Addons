class HlmGuestGuideCard extends HTMLElement {
  setConfig(config) {
    this.config = {
      events_entity: "sensor.hlm_public_events",
      favourites_entity: "sensor.hlm_guest_guide_favourites",
      ...config,
    };
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
  }

  set hass(hass) {
    this._hass = hass;
    if (!this.config) return;
    const eventsState = hass.states[this.config.events_entity];
    const favouritesState = hass.states[this.config.favourites_entity];
    const fingerprint = [
      eventsState?.attributes?.updated_at,
      favouritesState?.attributes?.updated_at,
      eventsState?.state,
      favouritesState?.state,
    ].join("|");
    if (fingerprint === this._fingerprint) return;
    this._fingerprint = fingerprint;
    this.render(eventsState, favouritesState);
  }

  escape(value = "") {
    return String(value).replace(/[&<>"']/g, (character) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    })[character]);
  }

  safeUrl(value = "") {
    try {
      const url = new URL(value);
      return ["http:", "https:"].includes(url.protocol) ? this.escape(url.href) : "";
    } catch (_error) {
      return "";
    }
  }

  placeMapsUrl(place = {}) {
    const query = [place.name, place.address]
      .map((value) => String(value || "").trim())
      .filter(Boolean)
      .join(", ");
    if (query) {
      return this.safeUrl(`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`);
    }
    return this.safeUrl(place.maps_url);
  }

  formatDateRange(start, end) {
    try {
      const startDate = new Date(`${start}T12:00:00Z`);
      const endDate = new Date(`${end}T12:00:00Z`);
      endDate.setUTCDate(endDate.getUTCDate() - 1);
      const longDate = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
      if (start === endDate.toISOString().slice(0, 10)) return longDate.format(startDate);
      const shortDate = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });
      return `${shortDate.format(startDate)} – ${longDate.format(endDate)}`;
    } catch (_error) {
      return start || "Date to be confirmed";
    }
  }

  renderEvent(event) {
    const isVisitIow = event.source === "viow";
    // VisitIOW destinations must be opened directly. Many destination sites
    // reject being embedded by the legacy hlm-external-link iframe wrapper.
    const external = isVisitIow ? this.safeUrl(event.external_url) : "";
    const sourceLabel = isVisitIow ? "Visit Isle of Wight" : "Local guide";
    return `<article class="event-card">
      <div class="event-meta"><div class="date-badge">${this.escape(this.formatDateRange(event.start, event.end))}</div><span class="source-badge ${isVisitIow ? "viow" : "local"}">${sourceLabel}</span></div>
      <h3>${this.escape(event.summary)}</h3>
      <p class="location"><span aria-hidden="true">⌖</span> ${this.escape(event.location || "Isle of Wight")}</p>
      <p class="description">${this.escape(event.description || "More information is available in the digital guide.")}</p>
      ${external ? `<a class="details" href="${external}" target="_blank" rel="noopener">Visit event website <span aria-hidden="true">→</span></a>` : ""}
    </article>`;
  }

  renderPlace(place, index) {
    const maps = this.placeMapsUrl(place);
    const initials = String(place.name || "Place").split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
    return `<article class="place-card" aria-label="${this.escape(place.name)}">
      <div class="place-hero shade-${index % 6}"><span>${this.escape(initials)}</span></div>
      <div class="place-content">
        <h3>${this.escape(place.name)}</h3>
        <p class="location">${this.escape(place.address || "Isle of Wight")}</p>
        <p class="description">${this.escape(place.description || "One of our favourite local places.")}</p>
        <div class="actions">
          ${maps ? `<a class="pill" href="${maps}" target="_blank" rel="noopener">Directions</a>` : ""}
        </div>
      </div>
    </article>`;
  }

  render(eventsState, favouritesState) {
    const events = Array.isArray(eventsState?.attributes?.events) ? eventsState.attributes.events : [];
    const favourites = Array.isArray(favouritesState?.attributes?.favourites) ? favouritesState.attributes.favourites : [];
    const updatedAt = eventsState?.attributes?.updated_at || favouritesState?.attributes?.updated_at;
    const updated = updatedAt ? new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" }).format(new Date(updatedAt)) : "pending";
    const eventCards = events.length ? events.map((event) => this.renderEvent(event)).join("") : '<p class="empty">Local events are being updated. Please check again shortly.</p>';
    const placeCards = favourites.length ? favourites.map((place, index) => this.renderPlace(place, index)).join("") : '<p class="empty">Favourite places are being updated. Please check again shortly.</p>';

    this.shadowRoot.innerHTML = `<style>
      :host{display:block;--ink:#17324d;--muted:#60758a;--sea:#087f8c;--foam:#edf8f7;--line:#dce7ec;--shadow:0 10px 28px rgba(28,61,82,.12)}
      *{box-sizing:border-box}ha-card{overflow:hidden;background:linear-gradient(180deg,#f4fbfc 0,#fff 24rem);color:var(--ink)}main{max-width:1500px;margin:auto;padding:clamp(1rem,2.4vw,2.25rem);font:16px/1.5 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}.eyebrow{margin:0;color:var(--sea);font-size:.82rem;font-weight:800;letter-spacing:.13em;text-transform:uppercase}h1{margin:.2rem 0 .3rem;font-size:clamp(1.9rem,4vw,3.4rem);line-height:1.05}h2{margin:2.2rem 0 .8rem;font-size:clamp(1.4rem,2.4vw,2rem)}h3{margin:.35rem 0;font-size:1.25rem;line-height:1.25}.intro,.location{color:var(--muted)}
      .events{display:grid;grid-auto-flow:column;grid-auto-columns:min(84vw,350px);gap:1rem;overflow-x:auto;scroll-snap-type:x mandatory;scroll-behavior:smooth;padding:.25rem .15rem 1.3rem;scrollbar-width:thin;scrollbar-color:#9dc5ca transparent}.event-card,.place-card{background:#fff;border:1px solid var(--line);border-radius:20px;box-shadow:var(--shadow);overflow:hidden}.event-card{display:flex;min-height:290px;flex-direction:column;padding:1.25rem;scroll-snap-align:start}.event-meta{display:flex;align-items:center;justify-content:space-between;gap:.5rem}.date-badge,.source-badge{align-self:flex-start;border-radius:999px;padding:.35rem .7rem;font-size:.78rem;font-weight:750}.date-badge{background:var(--foam);color:#086a73}.source-badge{background:#edf1f5;color:#52687c}.source-badge.viow{background:#fff1d7;color:#875c0a}.description{display:-webkit-box;overflow:hidden;-webkit-box-orient:vertical;-webkit-line-clamp:5;color:#40566a}.details{margin-top:auto;padding-top:.6rem;color:var(--sea);font-weight:750;text-decoration:none}
      .carousel-wrap{position:relative}.carousel{display:grid;grid-auto-flow:column;grid-auto-columns:min(84vw,350px);gap:1rem;overflow-x:auto;scroll-snap-type:x mandatory;scroll-behavior:smooth;padding:.25rem .15rem 1.3rem;scrollbar-width:thin;scrollbar-color:#9dc5ca transparent}.place-card{scroll-snap-align:start}.place-hero{display:grid;height:118px;place-items:center;background:linear-gradient(135deg,#168a94,#72c8bd)}.place-hero span{display:grid;width:66px;height:66px;place-items:center;border:2px solid rgba(255,255,255,.7);border-radius:50%;background:rgba(255,255,255,.18);color:#fff;font-size:1.45rem;font-weight:800}.shade-1{background:linear-gradient(135deg,#ee8c5b,#f6c36a)}.shade-2{background:linear-gradient(135deg,#4d7198,#8bb1c8)}.shade-3{background:linear-gradient(135deg,#7e6a9f,#c39ac8)}.shade-4{background:linear-gradient(135deg,#528b63,#9bc17b)}.shade-5{background:linear-gradient(135deg,#b2675e,#e5a98e)}.place-content{display:flex;min-height:275px;flex-direction:column;padding:1rem 1.1rem}.place-content .location{min-height:2.8em;margin:.2rem 0;font-size:.88rem}.actions{display:flex;flex-wrap:wrap;gap:.5rem;margin-top:auto}.pill{border-radius:999px;background:var(--sea);color:#fff;padding:.5rem .8rem;font-size:.86rem;font-weight:700;text-decoration:none}.pill.secondary{background:#e9f3f4;color:#17606a}
      .carousel-controls{display:flex;gap:.6rem;position:absolute;right:.2rem;top:-3.15rem}.carousel-controls button{width:42px;height:42px;border:1px solid var(--line);border-radius:50%;background:#fff;color:var(--ink);box-shadow:0 4px 14px rgba(28,61,82,.12);font-size:1.25rem;cursor:pointer}.empty{padding:1rem;border-radius:14px;background:#fffaf0}footer{margin-top:1rem;color:#8293a2;font-size:.78rem;text-align:right}
      @media(max-width:600px){main{padding:.9rem}.carousel-controls{display:none}.event-card{min-height:240px}.place-content{min-height:260px}}@media(prefers-reduced-motion:reduce){.carousel{scroll-behavior:auto}}
    </style><ha-card><main>
      <header><p class="eyebrow">Crossjack guest guide</p><h1>Events &amp; favourite places</h1><p class="intro">Local guide recommendations and Visit Isle of Wight listings, plus a few favourite places for your stay.</p></header>
      <section><h2>What’s on</h2><div class="events">${eventCards}</div></section>
      <section><h2>Our favourite places</h2><div class="carousel-wrap"><div class="carousel-controls"><button type="button" data-direction="-1" aria-label="Previous places">‹</button><button type="button" data-direction="1" aria-label="Next places">›</button></div><div class="carousel" tabindex="0">${placeCards}</div></div></section>
      <footer>Guide information last updated ${this.escape(updated)}</footer>
    </main></ha-card>`;
    const carousel = this.shadowRoot.querySelector(".carousel");
    this.shadowRoot.querySelectorAll("[data-direction]").forEach((button) => button.addEventListener("click", () => {
      carousel.scrollBy({ left: Number(button.dataset.direction) * Math.min(carousel.clientWidth * 0.9, 720), behavior: "smooth" });
    }));
  }

  getCardSize() { return 12; }
}

if (!customElements.get("hlm-guest-guide-card")) customElements.define("hlm-guest-guide-card", HlmGuestGuideCard);

class HlmExternalLinkCard extends HTMLElement {
  setConfig(config) { if (!config?.url) throw new Error("hlm-external-link-card requires a url"); this.config = config; this.render(); }
  render() {
    const esc = (v) => String(v ?? "").replace(/[&<>\"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
    this.attachShadow({mode:"open"}).innerHTML = `<style>:host{display:block;height:100%}a{width:100%;height:100%;min-height:92px;display:flex;align-items:center;justify-content:center;gap:.8rem;padding:1rem 1.2rem;border:1px solid #dce7ec;border-radius:20px;background:#fff;color:#17324d;box-shadow:0 10px 28px rgba(28,61,82,.12);font:inherit;text-align:left;text-decoration:none;cursor:pointer}ha-icon{--mdc-icon-size:2rem;color:#087f8c;flex:none}.copy{display:flex;flex-direction:column;gap:.18rem}.name{font-size:1.05rem;font-weight:750}.label{color:#60758a;font-size:.88rem}</style><a href="${esc(this.config.url)}" target="_blank" rel="noopener noreferrer" aria-label="${esc(this.config.name || "Open link")}"><ha-icon icon="${esc(this.config.icon || "mdi:open-in-new")}"></ha-icon><span class="copy"><span class="name">${esc(this.config.name || "Open link")}</span><span class="label">${esc(this.config.label)}</span></span></a>`;
  }
  getCardSize() { return 2; }
}
if (!customElements.get("hlm-external-link-card")) customElements.define("hlm-external-link-card", HlmExternalLinkCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "hlm-guest-guide-card",
  name: "HLM Guest Guide",
  description: "Combined local and VisitIOW events plus favourite places for Holiday Let Manager.",
});

const viewParams=new URLSearchParams(location.search);
let guide, section = ['house','places','home'].includes(viewParams.get('section')) ? viewParams.get('section') : 'house';
let resultCount=0, lastSearch='', itemContext={}, usageSending=false;
const usageQueue=[];
function eventId() {
  const bytes=crypto.getRandomValues(new Uint8Array(16)); bytes[6]=(bytes[6]&15)|64; bytes[8]=(bytes[8]&63)|128;
  const h=[...bytes].map(x=>x.toString(16).padStart(2,'0')).join('');
  return `${h.slice(0,8)}-${h.slice(8,12)}-${h.slice(12,16)}-${h.slice(16,20)}-${h.slice(20)}`;
}
function usage(action, details={}) {
  if (!guide?.stats_enabled || guide.preview) return;
  usageQueue.push({event_id:eventId(),kiosk:viewParams.get('kiosk') || guide.kiosk_id,action,section,...details});
  sendUsage();
}
async function sendUsage() {
  if (usageSending) return; usageSending=true;
  try {
    while (usageQueue.length) {
      const response=await fetch('./api/usage?property='+encodeURIComponent(guide.property?.property_id || ''),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(usageQueue[0]),keepalive:true});
      if (!response.ok) { if (response.status>=400 && response.status<500) { usageQueue.shift(); continue; } break; }
      usageQueue.shift();
    }
  } catch {} finally { usageSending=false; }
}
setInterval(sendUsage,10000);
function finishSearch() {
  const text=$('search').value;
  const key=JSON.stringify([section,text,$('filter').value,$('favourites').checked]);
  if (text.trim() && key!==lastSearch) {
    usage('search',{search_text:text,result_count:resultCount,category:$('filter').value,favourites_only:section==='places' && $('favourites').checked});
    lastSearch=key;
  }
}
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function safe(value) { try { const u = new URL(value); return ['http:','https:'].includes(u.protocol) ? u.href : ''; } catch { return ''; } }
const imageFile = f => (f.mime_type || '').startsWith('image/') || /\.(png|jpe?g|webp|avif|gif)$/i.test(f.title);
const attached = (key,value) => guide.files.filter(f => f[key] === value).sort((a,b) => Number(a.display_order || 0) - Number(b.display_order || 0));
const fileUrl = f => './media/' + encodeURIComponent(f.drive_file_id) + '?property=' + encodeURIComponent(guide.property.property_id);
function link(url,label) { url = safe(url); return url ? `<a class="action" href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(label)} ↗</a>` : ''; }
async function load(property) {
  try {
    const response = await fetch('./api/guide' + (property ? '?property=' + encodeURIComponent(property) : ''));
    guide = await response.json();
    if (!response.ok) throw Error(guide.error);
    $('property').textContent = guide.property?.name || 'Guide unavailable';
    $('notice').textContent = guide.preview ? 'Content preview · Draft items are visible here. Locations and links still need verification.' : guide.sync_issue ? 'Updates are temporarily unavailable. Showing the last downloaded guide.' : '';
    if (guide.preview && guide.properties.length > 1) {
      const select = document.createElement('select');
      select.setAttribute('aria-label','Preview property');
      select.innerHTML = guide.properties.map(p => `<option value="${esc(p.property_id)}" ${p.property_id === guide.property?.property_id ? 'selected' : ''}>${esc(p.name)}</option>`).join('');
      select.onchange = () => load(select.value);
      $('property').append(select);
    }
    $('sync').textContent = guide.synced_at ? (guide.preview ? 'Preview prepared ' : 'Content downloaded ') + new Date(guide.synced_at).toLocaleString('en-GB') : '';
    $('legal')?.remove();
    if (safe(guide.terms_url) && safe(guide.privacy_url)) {
      const legal = document.createElement('span'); legal.id = 'legal';
      legal.innerHTML = link(guide.terms_url,'Terms') + link(guide.privacy_url,'Privacy');
      document.querySelector('footer').append(legal);
    }
    setup();
    usage('page_view');
  } catch (error) { $('cards').innerHTML = `<p class="empty">${esc(error.message)} Please check back shortly.</p>`; }
}
function setup() {
  const house = section === 'house';
  document.querySelectorAll('[data-section]').forEach(b => b.classList.toggle('selected',b.dataset.section === section));
  $('intro').innerHTML = section === 'home' ? '<h1>Find your way back</h1><p>Scan a location to open it on your phone.</p>' : house ? '<h1>A little help around the house</h1><p>Practical instructions, appliance manuals and useful information for your stay.</p>' : '<h1>Explore our favourite places</h1><p>Our shared local guide. Places are ordered by straight-line distance when verified coordinates are available.</p>';
  $('favourite-label').hidden = section !== 'places';
  document.querySelector('.tools').hidden = section === 'home';
  const options = house ? [...new Set(guide.topics.map(t => t.category))].filter(Boolean).sort().map(name => ({id:name,name})) : guide.categories.map(c => ({id:c.category_id,name:c.name}));
  $('filter').innerHTML = '<option value="">All categories</option>' + options.map(x => `<option value="${esc(x.id)}">${esc(x.name)}</option>`).join('');
  $('search').value = ''; lastSearch=''; render();
}
function render() {
  if (!guide.property) { $('count').textContent = ''; $('cards').innerHTML = '<p class="empty">There is no published guide for this property yet.</p>'; return; }
  if (section === 'home') {
    $('count').textContent = '';
    $('cards').innerHTML = `<article class="card"><div class="body"><h2>${esc(guide.property.name)}</h2><p>${esc(guide.property.arrival_notes || 'Your property location will appear here once it has been verified.')}</p><button id="property-location">View location</button></div></article>`;
    $('property-location').onclick = () => openLocation(guide.property); return;
  }
  const house = section === 'house', search = $('search').value.toLowerCase(), category = $('filter').value;
  let rows = (house ? guide.topics : guide.places).filter(x => JSON.stringify(house ? [x.title,x.instructions] : [x.name,x.description,x.recommendation]).toLowerCase().includes(search));
  if (category) rows = rows.filter(x => house ? x.category === category : x.categories.includes(category));
  if (!house && $('favourites').checked) rows = rows.filter(x => x.favourite === true || x.favourite === 'TRUE');
  resultCount=rows.length;
  $('count').textContent = rows.length + (house ? ' house-guide items' : ' places');
  $('cards').innerHTML = rows.map(x => {
    const photo = !house && attached('place_id',x.place_id).find(imageFile);
    const distance = x.distance == null ? 'Distance not yet available' : x.distance.toFixed(1) + ' miles';
    const description = x.recommendation || x.description || 'View this place for more information.';
    return `<article class="card">${photo ? `<img src="${fileUrl(photo)}" alt="${esc(x.name)}" loading="lazy">` : ''}<div class="body"><span class="eyebrow">${house ? esc(x.category) : esc(distance)}</span><h2>${esc(house ? x.title : x.name)}</h2>${!house ? `<p>${esc(description.slice(0,180))}${description.length > 180 ? '…' : ''}</p>` : ''}<button data-open="${esc(house ? x.topic_id : x.place_id)}">${house ? 'Read guide' : 'View place'} →</button></div></article>`;
  }).join('') || '<p class="empty">No items match your search.</p>';
  document.querySelectorAll('[data-open]').forEach(b => b.onclick = () => house ? openTopic(guide.topics.find(x => x.topic_id === b.dataset.open)) : openPlace(guide.places.find(x => x.place_id === b.dataset.open)));
}
function photos(files) { return `<div class="photo-grid">${files.filter(imageFile).map(f => `<img src="${fileUrl(f)}" alt="${esc(f.title)}" loading="lazy">`).join('')}</div>`; }
function placeText(text) { return String(text || '').split(/\r?\n|\u2028|\u2029/).map(p => p.trim()).filter(Boolean).map(p => `<p>${esc(p)}</p>`).join(''); }
function filesPanel(files) { return files.filter(f => !imageFile(f)).map(f => `<button data-file="${esc(f.drive_file_id)}">View ${esc(f.title)}</button>`).join(''); }
function modal(html) {
  $('detail-content').innerHTML = html; $('detail').showModal(); $('detail').scrollTop = 0;
  document.querySelectorAll('[data-file]').forEach(b => b.onclick = () => {
    const file=guide.files.find(f=>f.drive_file_id===b.dataset.file);
    usage('document_open',{item_id:file?.attachment_id || b.dataset.file,item_name:file?.title || b.textContent});
    $('detail-content').querySelector('.pdf-view')?.remove();
    const frame = document.createElement('iframe'); frame.className = 'pdf-view'; frame.title = b.textContent;
    frame.src = './pdf-viewer.html?file=' + encodeURIComponent(b.dataset.file) + '&property=' + encodeURIComponent(guide.property.property_id);
    $('detail-content').append(frame); frame.scrollIntoView({behavior:'smooth'});
  });
  $('detail-content').querySelectorAll('a.action,a.instruction-link').forEach(a=>a.addEventListener('click',()=>usage('link_tap',{...itemContext,item_name:a.textContent})));
}
function guideLink(topic) {
  const url = safe(topic.manual_url);
  return link(url, 'Open external guide');
}
function topicInstructions(topic,files=[]) {
  const used=new Set(), usedFiles=new Set(), links=topic.instruction_links || [];
  const html=String(topic.instructions || '').replace(/\n{3,}/g,'\n\n').split('\n').map(line=>{
    const text=line.trim(), key=text.toLowerCase();
    const file=files.find(f=>!imageFile(f) && f.title && (key===f.title.trim().toLowerCase() || key.startsWith(f.title.trim().toLowerCase()+' ')));
    if (file) {
      usedFiles.add(file.drive_file_id);
      return `<button class="instruction-link" data-file="${esc(file.drive_file_id)}">${esc(text)}</button>`;
    }
    const match=links.find(x=>safe(x.url) && x.label && (key===x.label.trim().toLowerCase() || key.startsWith(x.label.trim().toLowerCase()+' ')));
    if (!match) return esc(line);
    used.add(match.url);
    return `<a class="instruction-link" href="${esc(safe(match.url))}" target="_blank" rel="noopener noreferrer">${esc(text)} ↗</a>`;
  }).join('\n');
  return {html,remaining:links.filter(x=>!used.has(x.url)),remainingFiles:files.filter(f=>!usedFiles.has(f.drive_file_id))};
}
function openTopic(topic) {
  finishSearch(); itemContext={item_id:topic.topic_id,item_name:topic.title}; usage('topic_open',itemContext);
  const files = attached('topic_id',topic.topic_id);
  const instructions=topicInstructions(topic,files);
  if (files.some(imageFile)) usage('photos_shown',{...itemContext,result_count:files.filter(imageFile).length});
  modal(`<span class="eyebrow">${esc(topic.category)}</span><h2>${esc(topic.title)}</h2><div class="instructions">${instructions.html}</div>${photos(files)}<div class="actions">${filesPanel(instructions.remainingFiles)}${guideLink(topic)}${link(topic.video_url,'Watch video')}${instructions.remaining.map(x => link(x.url,x.label)).join('')}</div><p class="distance">External guides and videos need an internet connection.</p>`);
}
function transfer(place,property = false) {
  const params = new URLSearchParams({property:guide.property.property_id}); if (!property) params.set('place',place.place_id);
  const qr = kind => './api/qr?' + params.toString() + '&kind=' + kind;
  return `<section class="transfer"><h2>Take this location with you</h2><div class="qr-grid">${place.maps_url ? `<div class="qr-box"><img src="${qr('maps')}" alt="Scan to open Google Maps"><strong>Google Maps</strong><p>Scan with your phone camera to open the location.</p></div>` : ''}</div></section>`;
}
function openPlace(place) {
  finishSearch(); itemContext={item_id:place.place_id,item_name:place.name}; usage('place_open',itemContext);
  const files = attached('place_id',place.place_id);
  if (files.some(imageFile)) usage('photos_shown',{...itemContext,result_count:files.filter(imageFile).length});
  if (place.maps_url) usage('qr_shown',itemContext);
  modal(`<span class="eyebrow">${place.distance == null ? 'Distance unavailable' : place.distance.toFixed(1) + ' miles as the crow flies'}</span><h2>${esc(place.name)}</h2>${photos(files)}${place.recommendation ? `<div class="place-copy">${placeText(place.recommendation)}</div>` : ''}<div class="place-copy">${placeText(place.description)}</div><p>${esc(place.address)}</p>${place.discount ? `<p><strong>Guest offer:</strong> ${esc(place.discount)}</p>` : ''}<div class="actions">${link(place.custom_url,place.custom_link_label || 'More information')}${filesPanel(files)}${guide.google_available && place.google_place_id ? '<button id="live-button">Check current opening hours</button>' : ''}</div><div id="live-data" hidden></div>${transfer(place)}`);
  if ($('live-button')) $('live-button').onclick = () => liveDetails(place);
}
function openLocation(place) { itemContext={item_id:place.property_id,item_name:place.name}; if (place.maps_url) usage('qr_shown',itemContext); modal(`<h2>${esc(place.name)}</h2><p>${esc(place.arrival_notes || 'Location verification is pending.')}</p>${transfer(place,true)}`); }
async function liveDetails(place) {
  const panel = $('live-data'); panel.hidden = false; panel.textContent = 'Checking Google…';
  try {
    const response = await fetch('./api/places/' + encodeURIComponent(place.place_id)); const d = await response.json(); if (!response.ok) throw Error(d.error);
    panel.innerHTML = '<img class="google-logo" src="https://maps.gstatic.com/mapfiles/api-3/images/powered-by-google-on-white3.png" alt="Powered by Google">' + (d.currentOpeningHours ? `<p>${d.currentOpeningHours.openNow === true ? 'Open now' : d.currentOpeningHours.openNow === false ? 'Closed now' : 'Current opening status unavailable'}</p><ul>${(d.currentOpeningHours.weekdayDescriptions || []).map(h => `<li>${esc(h)}</li>`).join('')}</ul>` : '<p>Opening hours are unavailable.</p>') + link(d.googleMapsUri,'View on Google Maps') + (d.attributions || []).map(a => link(a.uri,a.provider || 'Data provider')).join('');
  } catch (error) { panel.textContent = error.message; }
}
document.querySelectorAll('[data-section]').forEach(b => b.onclick = () => { finishSearch(); section = b.dataset.section; setup(); usage('section_open'); });
$('search').oninput = () => { lastSearch=''; render(); };
$('search').onkeydown = e => { if (e.key==='Enter') { e.preventDefault(); finishSearch(); } };
$('search').onblur = finishSearch;
$('search').maxLength=2000;
$('filter').onchange = () => { render(); usage('category_filter',{category:$('filter').value,result_count:resultCount}); };
$('favourites').onchange = () => { render(); usage('favourites_filter',{favourites_only:$('favourites').checked,result_count:resultCount}); };
document.addEventListener('visibilitychange',()=>{ if (document.hidden) { finishSearch(); sendUsage(); } });
$('close').onclick = () => $('detail').close(); $('detail').addEventListener('close',() => $('detail-content').replaceChildren());
load(viewParams.get('property'));

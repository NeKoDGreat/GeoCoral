/* GeoCoral map page.
   Fetches /api/sanctuaries/ and /api/coral-records/ (same-origin, no
   auth needed for reads) and plots them on a Leaflet map, colored by
   effective_label. Filters re-fetch with query params rather than
   filtering client-side, so this stays correct as records grow. */

const DEFAULT_CENTER = [7.05, 125.68]; // Samal Island, Davao Gulf
const DEFAULT_ZOOM = 12;

const map = L.map("map", { zoomControl: true }).setView(DEFAULT_CENTER, DEFAULT_ZOOM);

L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
  subdomains: "abcd",
  maxZoom: 19,
}).addTo(map);

let markersLayer = L.layerGroup().addTo(map);
let sanctuaryMarkersLayer = L.layerGroup().addTo(map);

function markerColor(label) {
  return label === "bleached" ? "#d8cfc0" : "#ff6f5e";
}

function buildCoralIcon(label) {
  const color = markerColor(label);
  return L.divIcon({
    className: "",
    html: `<div style="width:14px;height:14px;border-radius:50%;background:${color};border:2px solid rgba(10,31,43,0.6);box-shadow:0 0 0 3px rgba(255,255,255,0.08);"></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });
}

function popupHtml(record) {
  const labelClass = record.effective_label === "bleached" ? "bleached" : "healthy";
  const labelText = record.effective_label === "bleached" ? "Bleached" : "Healthy";
  const confidencePct = (record.confidence * 100).toFixed(1);
  const date = new Date(record.captured_at).toLocaleDateString(undefined, {
    year: "numeric", month: "short", day: "numeric",
  });
  return `
    <p class="popup-label ${labelClass}">${labelText}</p>
    <div class="popup-meta">
      ${record.sanctuary_name}<br>
      ${record.latitude.toFixed(5)}, ${record.longitude.toFixed(5)}<br>
      ${record.depth_m != null ? record.depth_m + "m depth &middot; " : ""}${date}<br>
      Confidence: ${confidencePct}%
    </div>
    ${record.image ? `<img class="popup-photo" src="${record.image}" alt="Coral photo">` : ""}
  `;
}

async function loadSanctuaries() {
  const res = await fetch("/api/sanctuaries/");
  const data = await res.json();
  const select = document.getElementById("sanctuary-filter");
  sanctuaryMarkersLayer.clearLayers();

  data.results.forEach((s) => {
    const option = document.createElement("option");
    option.value = s.id;
    option.textContent = s.name;
    select.appendChild(option);

    if (s.center_latitude != null && s.center_longitude != null) {
      L.circleMarker([s.center_latitude, s.center_longitude], {
        radius: 5,
        color: "#6fe3c8",
        weight: 1,
        fillOpacity: 0.15,
      })
        .bindTooltip(s.name, { direction: "top" })
        .addTo(sanctuaryMarkersLayer);
    }
  });
}

async function loadRecords() {
  const sanctuaryId = document.getElementById("sanctuary-filter").value;
  const label = document.getElementById("label-filter").value;

  const params = new URLSearchParams();
  if (sanctuaryId) params.set("sanctuary", sanctuaryId);
  if (label) params.set("label", label);

  const res = await fetch(`/api/coral-records/?${params.toString()}`);
  const data = await res.json();

  markersLayer.clearLayers();
  let bleachedCount = 0;

  data.results.forEach((record) => {
    if (record.effective_label === "bleached") bleachedCount += 1;
    L.marker([record.latitude, record.longitude], {
      icon: buildCoralIcon(record.effective_label),
    })
      .bindPopup(popupHtml(record))
      .addTo(markersLayer);
  });

  document.getElementById("stat-total").textContent = data.results.length;
  document.getElementById("stat-bleached").textContent = bleachedCount;
}

document.getElementById("sanctuary-filter").addEventListener("change", loadRecords);
document.getElementById("label-filter").addEventListener("change", loadRecords);

loadSanctuaries().then(loadRecords);
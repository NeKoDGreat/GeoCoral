/* GeoCoral upload page.
   Captures GPS from the browser (falls back to manual entry), loads
   sanctuaries for the dropdown, and submits the photo + metadata to
   the coral-records API, displaying the classification result the
   server returns. */

let capturedLat = null;
let capturedLon = null;
let gpsSource = "device";

function setDefaultCapturedAt() {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  document.getElementById("captured_at").value = now.toISOString().slice(0, 16);
}
setDefaultCapturedAt();

function showManualLatLon(message) {
  document.getElementById("gps-readout").textContent = message;
  document.getElementById("gps-readout").classList.remove("acquired");
  document.getElementById("manual-latlon").style.display = "flex";
  gpsSource = "manual";
}

if ("geolocation" in navigator) {
  navigator.geolocation.getCurrentPosition(
    (position) => {
      capturedLat = position.coords.latitude;
      capturedLon = position.coords.longitude;
      gpsSource = "device";
      const readout = document.getElementById("gps-readout");
      readout.textContent = `${capturedLat.toFixed(5)}, ${capturedLon.toFixed(5)} (accuracy ~${Math.round(position.coords.accuracy)}m)`;
      readout.classList.add("acquired");
      document.getElementById("gps-hint").textContent = "Captured from your device.";
    },
    () => {
      showManualLatLon("Location unavailable — enter it manually below.");
    },
    { enableHighAccuracy: true, timeout: 10000 }
  );
} else {
  showManualLatLon("Your browser doesn't support location — enter it manually below.");
}

async function loadSanctuaries() {
  const res = await fetch("/api/sanctuaries/");
  const data = await res.json();
  const select = document.getElementById("sanctuary");
  data.results.forEach((s) => {
    const option = document.createElement("option");
    option.value = s.id;
    option.textContent = `${s.name} (${s.area_code})`;
    select.appendChild(option);
  });
}
loadSanctuaries();

function getCsrfToken() {
  return document.querySelector("[name=csrfmiddlewaretoken]").value;
}

function resolveLatLon() {
  if (gpsSource === "device" && capturedLat != null && capturedLon != null) {
    return { lat: capturedLat, lon: capturedLon };
  }
  const lat = parseFloat(document.getElementById("manual-lat").value);
  const lon = parseFloat(document.getElementById("manual-lon").value);
  if (Number.isNaN(lat) || Number.isNaN(lon)) return null;
  return { lat, lon };
}

document.getElementById("upload-form").addEventListener("submit", async (event) => {
  event.preventDefault();

  const errorBox = document.getElementById("error");
  const resultBox = document.getElementById("result");
  const submitBtn = document.getElementById("submit-btn");
  const statusEl = document.getElementById("submit-status");
  errorBox.style.display = "none";
  resultBox.style.display = "none";

  const latlon = resolveLatLon();
  if (!latlon) {
    errorBox.textContent = "Location is required — allow device location or enter latitude/longitude manually.";
    errorBox.style.display = "block";
    return;
  }

  const imageInput = document.getElementById("image");
  if (!imageInput.files.length) {
    errorBox.textContent = "Choose a photo before submitting.";
    errorBox.style.display = "block";
    return;
  }

  const formData = new FormData();
  formData.append("image", imageInput.files[0]);
  formData.append("latitude", latlon.lat);
  formData.append("longitude", latlon.lon);
  formData.append("captured_at", document.getElementById("captured_at").value);
  formData.append("sanctuary", document.getElementById("sanctuary").value);
  formData.append("area_code", document.getElementById("area_code").value);
  const depth = document.getElementById("depth_m").value;
  if (depth) formData.append("depth_m", depth);
  formData.append("gps_source", gpsSource);

  submitBtn.disabled = true;
  statusEl.textContent = "Classifying — this can take a few seconds...";

  try {
    const res = await fetch("/api/coral-records/", {
      method: "POST",
      headers: { "X-CSRFToken": getCsrfToken() },
      body: formData,
      credentials: "same-origin",
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(
        errData.detail || JSON.stringify(errData) || `Server returned ${res.status}`
      );
    }

    const record = await res.json();
    const labelClass = record.effective_label === "bleached" ? "bleached" : "healthy";
    const labelText = record.effective_label === "bleached" ? "Bleached" : "Healthy";
    const confidencePct = (record.confidence * 100).toFixed(1);

    resultBox.innerHTML = `
      <div class="result-card">
        <p class="result-label ${labelClass}">${labelText}</p>
        <div class="result-meta">
          Model confidence: ${confidencePct}%<br>
          Recorded at ${record.latitude.toFixed(5)}, ${record.longitude.toFixed(5)}
        </div>
      </div>
    `;
    resultBox.style.display = "block";
    statusEl.textContent = "";
    document.getElementById("upload-form").reset();
    setDefaultCapturedAt();
  } catch (err) {
    errorBox.textContent = `Submission failed: ${err.message}`;
    errorBox.style.display = "block";
    statusEl.textContent = "";
  } finally {
    submitBtn.disabled = false;
  }
});
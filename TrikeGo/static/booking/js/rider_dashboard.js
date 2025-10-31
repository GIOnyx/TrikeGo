// Rider dashboard JS (moved from template)
(function(){
    const cfg = window.RIDER_DASH_CONFIG || {};
    const ORS_API_KEY = cfg.ORS_API_KEY || '';
    const userId = cfg.userId || null;
    const csrfToken = cfg.csrfToken || '';

    // Small helper: escape HTML
    function escapeHtml(str) {
        return String(str).replace(/[&<>"']/g, function (s) {
            return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[s];
        });
    }

    // ORSAutocomplete class (same behavior as inline version)
    class ORSAutocomplete {
        constructor(inputId, resultsId, latFieldId, lonFieldId, onSelectCallback) {
            this.input = document.getElementById(inputId);
            this.results = document.getElementById(resultsId);
            this.latField = document.getElementById(latFieldId);
            this.lonField = document.getElementById(lonFieldId);
            this.onSelectCallback = onSelectCallback;
            this.timeout = null;
            if (!this.input) return;
            this.init();
        }
        init() {
            this.input.addEventListener('input', (e) => this.handleInput(e));
            document.addEventListener('click', (e) => {
                if (!this.input.contains(e.target) && this.results && !this.results.contains(e.target)) {
                    this.results.classList.remove('active');
                }
            });
        }
        handleInput(e) {
            const query = e.target.value.trim();
            clearTimeout(this.timeout);
            if (query.length < 3) { if (this.results) { this.results.innerHTML = ''; this.results.classList.remove('active'); } return; }
            if (this.results) { this.results.innerHTML = '<div class="loading">Searching...</div>'; this.results.classList.add('active'); }
            this.timeout = setTimeout(() => this.search(query), 300);
        }
        async search(query) {
            try {
                const params = new URLSearchParams({ api_key: ORS_API_KEY, text: query, size: 10, 'boundary.country': 'PH' });
                const url = `https://api.openrouteservice.org/geocode/search?${params.toString()}`;
                const response = await fetch(url);
                const data = await response.json();
                let features = data.features || [];
                try { if (window.map) { const center = window.map.getCenter(); features.forEach(f => { const [lon, lat] = f.geometry.coordinates; f.__distance = window.map.distance(center, L.latLng(lat, lon)); }); features.sort((a,b) => (a.__distance||0) - (b.__distance||0)); } } catch(e){}
                this.displayResults(features);
            } catch (error) {
                console.error('Autocomplete API error:', error);
                if (this.results) this.results.innerHTML = '<div class="loading">Error loading results</div>';
            }
        }
        displayResults(features) {
            if (!this.results) return;
            this.results.innerHTML = '';
            if (features.length === 0) { this.results.innerHTML = '<div class="loading">No results found</div>'; return; }
            features.forEach(feature => {
                const item = document.createElement('div'); item.className = 'autocomplete-item';
                const props = feature.properties || {};
                const name = props.label || props.name || 'Unknown';
                let distanceText = '';
                if (feature.__distance != null) { distanceText = ` <small style="color:#999;margin-left:8px;">(${Math.round(feature.__distance)}m)</small>`; }
                item.innerHTML = `<strong>${name}</strong>${distanceText}`;
                item.addEventListener('click', () => this.selectResult(feature));
                this.results.appendChild(item);
            });
            this.results.classList.add('active');
        }
        selectResult(feature) {
            const coords = feature.geometry.coordinates; const lat = coords[1]; const lon = coords[0]; const props = feature.properties || {};
            this.input.value = props.label || props.name || `${lat}, ${lon}`;
            if (this.latField) this.latField.value = lat; if (this.lonField) this.lonField.value = lon;
            if (this.results) { this.results.classList.remove('active'); this.results.innerHTML = ''; }
            if (this.onSelectCallback) this.onSelectCallback(lat, lon);
        }
    }

    // Chat modal helpers (rider)
    let _chatModalBookingId = null;
    let _chatModalPolling = null;
    const chatModal = document.getElementById('chatModal');
    const chatModalMessages = document.getElementById('chatModalMessages');
    const chatModalForm = document.getElementById('chatModalForm');
    const chatModalInput = document.getElementById('chatModalInput');
    const chatModalTitle = document.getElementById('chatModalTitle');
    const chatModalClose = document.getElementById('chatModalClose');

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) { cookieValue = decodeURIComponent(cookie.substring(name.length + 1)); break; }
            }
        }
        return cookieValue;
    }

    function openChatModal(bookingId) {
        _chatModalBookingId = bookingId;
        if (!chatModal) return;
        chatModal.style.display = 'block';
        chatModal.scrollIntoView({ behavior: 'smooth' });
        if (chatModalTitle) chatModalTitle.textContent = `Chat (Booking ${bookingId})`;
        loadModalMessages();
    if (!_chatModalBookingId) return;
    if (window._chatModalPolling) clearInterval(window._chatModalPolling);
    // Poll less often for chat; consider switching to WebSockets (Channels) in production
    window._chatModalPolling = setInterval(loadModalMessages, 6000);
    }

    function closeChatModal() { if (!chatModal) return; chatModal.style.display = 'none'; _chatModalBookingId = null; if (window._chatModalPolling) { clearInterval(window._chatModalPolling); window._chatModalPolling = null; } }

    // ORS / routing rate-limit guard and previous-coords cache to avoid excessive routing requests
    let _orsRateLimitedUntil = 0;
    let _prevDriverToPickupCoords = null;
    let _prevPickupToDestCoords = null;
    let _lastDTData = null;
    let _lastRDData = null;

    async function loadModalMessages() {
        if (!_chatModalBookingId || !chatModalMessages) return;
        const res = await fetch(`/chat/api/booking/${_chatModalBookingId}/messages/`, { credentials: 'same-origin' });
        if (!res.ok) { chatModalMessages.innerHTML = '<p class="muted">Unable to load messages.</p>'; return; }
        const data = await res.json(); chatModalMessages.innerHTML = '';
        if (!data.messages || data.messages.length === 0) { chatModalMessages.innerHTML = '<p class="muted">No messages yet.</p>'; return; }
        let lastDate = null;
        data.messages.forEach(m => {
            const msgDate = new Date(m.timestamp).toDateString();
            if (msgDate !== lastDate) { const sep = document.createElement('div'); sep.className = 'chat-date-sep'; sep.textContent = new Date(m.timestamp).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' }); chatModalMessages.appendChild(sep); lastDate = msgDate; }
            const div = document.createElement('div'); const own = (m.sender_id == userId); div.className = own ? 'chat-msg-own' : 'chat-msg-other'; div.innerHTML = `<div class="chat-msg-meta">${m.sender_username} • ${new Date(m.timestamp).toLocaleTimeString()}</div><div>${escapeHtml(m.message)}</div>`; chatModalMessages.appendChild(div);
        });
        try { const newest = chatModalMessages.lastElementChild; chatModalMessages.scrollTo({ top: chatModalMessages.scrollHeight, behavior: 'smooth' }); if (newest) { newest.classList.add('flash-animate'); setTimeout(() => newest.classList.remove('flash-animate'), 900); } } catch(e) { chatModalMessages.scrollTop = chatModalMessages.scrollHeight; }
    }

    if (chatModalClose) chatModalClose.addEventListener('click', (e) => { e.preventDefault(); closeChatModal(); });

    if (chatModalForm) chatModalForm.addEventListener('submit', async (e) => {
        e.preventDefault(); if (!_chatModalBookingId) return; const text = (chatModalInput.value || '').trim(); if (!text) return;
        const res = await fetch(`/chat/api/booking/${_chatModalBookingId}/messages/send/`, { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') }, body: JSON.stringify({ message: text }) });
        if (!res.ok) { alert('Failed to send message'); return; }
        chatModalInput.value = ''; loadModalMessages();
    });

    // Export small helpers used by other pieces of UI
    window.openChatModal = openChatModal; window.closeChatModal = closeChatModal;

    // Initialize map and autocomplete on DOMContentLoaded
    document.addEventListener('DOMContentLoaded', () => {
        try {
            window.map = L.map('map').setView([14.5995, 120.9842], 12);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap contributors', maxZoom: 19 }).addTo(window.map);
            if (navigator.geolocation) navigator.geolocation.getCurrentPosition((pos) => { window.map.setView([pos.coords.latitude, pos.coords.longitude], 15); }, () => {}, { enableHighAccuracy: true, timeout: 5000 });
        } catch (e) { console.warn('Leaflet/map init failed', e); }

        // Keep track of the last focused booking input (so clicks on the map can still target it)
        window._lastFocusedBookingInputId = null;
        const bookingInputIds = ['pickup_location_input', 'destination_location_input'];
        document.addEventListener('focusin', (ev) => {
            try {
                const id = ev.target && ev.target.id ? ev.target.id : null;
                if (bookingInputIds.includes(id)) window._lastFocusedBookingInputId = id;
            } catch(e) {}
        });

        // Helper functions to place/update temporary markers for inputs (when user selects an address or clicks map)
        function setPickupInputMarker(lat, lon, label) {
            try {
                const latLng = [lat, lon];
                if (!pickupMarker) {
                    const pickupIcon = L.divIcon({ className: 'pickup-marker', html: '<div style="background: #ffc107; width: 20px; height: 20px; border-radius: 50%; border: 2px solid white;"></div>', iconSize: [20,20] });
                    pickupMarker = L.marker(latLng, { icon: pickupIcon }).addTo(window.map).bindPopup(label || 'Pickup');
                } else {
                    pickupMarker.setLatLng(latLng);
                    if (pickupMarker.getPopup()) pickupMarker.getPopup().setContent(label || 'Pickup');
                }
                try { window.map.setView(latLng, 16); } catch(e){}
            } catch(e) { console.warn('setPickupInputMarker failed', e); }
        }

        function setDestinationInputMarker(lat, lon, label) {
            try {
                const latLng = [lat, lon];
                if (!destinationMarker) {
                    const destIcon = L.divIcon({ className: 'dest-marker', html: '<div style="background: #007bff; width: 20px; height: 20px; border-radius: 50%; border: 2px solid white;"></div>', iconSize: [20,20] });
                    destinationMarker = L.marker(latLng, { icon: destIcon }).addTo(window.map).bindPopup(label || 'Destination');
                } else {
                    destinationMarker.setLatLng(latLng);
                    if (destinationMarker.getPopup()) destinationMarker.getPopup().setContent(label || 'Destination');
                }
                try { window.map.setView(latLng, 16); } catch(e){}
            } catch(e) { console.warn('setDestinationInputMarker failed', e); }
        }

        try { new ORSAutocomplete('pickup_location_input', 'pickup-results', 'id_pickup_latitude', 'id_pickup_longitude', (lat, lon) => { try { window.map.setView([lat, lon], 16); setPickupInputMarker(lat, lon); } catch(e){} }); } catch(e){}
        try { new ORSAutocomplete('destination_location_input', 'destination-results', 'id_destination_latitude', 'id_destination_longitude', (lat, lon) => { try { window.map.setView([lat, lon], 16); setDestinationInputMarker(lat, lon); } catch(e){} }); } catch(e){}

        // When hidden lat/lon fields are programmatically updated elsewhere, reflect them on the map.
        try {
            const hidPickupLat = document.getElementById('id_pickup_latitude');
            const hidPickupLon = document.getElementById('id_pickup_longitude');
            const hidDestLat = document.getElementById('id_destination_latitude');
            const hidDestLon = document.getElementById('id_destination_longitude');
            function tryPlacePickupFromHidden() {
                try {
                    const lat = parseFloat(hidPickupLat?.value);
                    const lon = parseFloat(hidPickupLon?.value);
                    if (!Number.isNaN(lat) && !Number.isNaN(lon)) setPickupInputMarker(lat, lon, document.getElementById('pickup_location_input')?.value || 'Pickup');
                } catch(e){}
            }
            function tryPlaceDestFromHidden() {
                try {
                    const lat = parseFloat(hidDestLat?.value);
                    const lon = parseFloat(hidDestLon?.value);
                    if (!Number.isNaN(lat) && !Number.isNaN(lon)) setDestinationInputMarker(lat, lon, document.getElementById('destination_location_input')?.value || 'Destination');
                } catch(e){}
            }
            if (hidPickupLat && hidPickupLon) {
                hidPickupLat.addEventListener('change', tryPlacePickupFromHidden);
                hidPickupLon.addEventListener('change', tryPlacePickupFromHidden);
            }
            if (hidDestLat && hidDestLon) {
                hidDestLat.addEventListener('change', tryPlaceDestFromHidden);
                hidDestLon.addEventListener('change', tryPlaceDestFromHidden);
            }
        } catch(e) {}

        // Map click -> reverse geocode into focused booking input
        try {
            if (window.map) {
                async function reverseGeocodeAndFill(lat, lon) {
                    const key = ORS_API_KEY || (window.RIDER_DASH_CONFIG && window.RIDER_DASH_CONFIG.ORS_API_KEY) || '';
                    if (!key) return null;
                    const url = `https://api.openrouteservice.org/geocode/reverse?api_key=${encodeURIComponent(key)}&point.lat=${encodeURIComponent(lat)}&point.lon=${encodeURIComponent(lon)}&size=1`;
                    try {
                        const res = await fetch(url);
                        if (!res.ok) return null;
                        const data = await res.json();
                        const feat = (data.features && data.features[0]) ? data.features[0] : null;
                        const label = feat?.properties?.label || feat?.properties?.name || null;
                        return label ? { label, props: feat.properties } : null;
                    } catch (e) { console.warn('Reverse geocode failed', e); return null; }
                }

                window.map.on('click', async function(e) {
                    try {
                        // Prefer the element that was last focused in booking inputs (clicking the map itself moves focus away)
                        const lastId = window._lastFocusedBookingInputId || null;
                        const active = document.activeElement;
                        const activeId = (active && (active.id || active.getAttribute('id'))) ? (active.id || active.getAttribute('id')) : null;
                        const id = (activeId && ['pickup_location_input','destination_location_input'].includes(activeId)) ? activeId : lastId;
                        if (!id) return;
                        const lat = e.latlng.lat; const lon = e.latlng.lng;
                        const result = await reverseGeocodeAndFill(lat, lon);
                        const label = result?.label || `${lat.toFixed(5)}, ${lon.toFixed(5)}`;
                        // fill visible input and hidden lat/lon fields
                        const inputEl = document.getElementById(id);
                        if (inputEl) inputEl.value = label;
                        if (id === 'pickup_location_input') {
                            const hLat = document.getElementById('id_pickup_latitude');
                            const hLon = document.getElementById('id_pickup_longitude');
                            if (hLat) hLat.value = lat; if (hLon) hLon.value = lon;
                            // show marker
                            setPickupInputMarker(lat, lon, label);
                        } else if (id === 'destination_location_input') {
                            const hLat = document.getElementById('id_destination_latitude');
                            const hLon = document.getElementById('id_destination_longitude');
                            if (hLat) hLat.value = lat; if (hLon) hLon.value = lon;
                            // show marker
                            setDestinationInputMarker(lat, lon, label);
                        }
                    } catch (err) { console.warn('Map click handler error', err); }
                });
            }
        } catch (e) { /* non-critical */ }
    });
            // Booking / tracking variables and helpers
        let trackingInterval = null;
            let driverMarker = null;
            let pickupMarker = null;
            let destinationMarker = null;
            let driverToRiderRouteLayer = null;
            let riderToDestRouteLayer = null;
            let initialRouteLoadDone = false;
        let currentTrackedBookingId = null;

            async function updateAll(bookingId) {
                const loader = document.getElementById('route-loader');
                try {
                    if (!initialRouteLoadDone && loader) { loader.classList.remove('hidden'); loader.setAttribute('aria-hidden', 'false'); }
                    const infoRes = await fetch(`/api/booking/${bookingId}/route_info/`);
                    if (!infoRes.ok) {
                        if (!initialRouteLoadDone && loader) { loader.classList.add('hidden'); loader.setAttribute('aria-hidden', 'true'); }
                        console.error('Failed to fetch route info:', infoRes.status);
                        return;
                    }
                    const info = await infoRes.json();
                    if (info.status !== 'success') {
                        if (!initialRouteLoadDone && loader) { loader.classList.add('hidden'); loader.setAttribute('aria-hidden', 'true'); }
                        console.error('Route info error:', info.message);
                        return;
                    }

                    const dLat = Number(info.driver_lat);
                    const dLon = Number(info.driver_lon);
                    const pLat = Number(info.pickup_lat);
                    const pLon = Number(info.pickup_lon);
                    const xLat = Number(info.destination_lat);
                    const xLon = Number(info.destination_lon);

                    const hasDriver = Number.isFinite(dLat) && Number.isFinite(dLon);
                    const hasPickup = Number.isFinite(pLat) && Number.isFinite(pLon);
                    const hasDest = Number.isFinite(xLat) && Number.isFinite(xLon);

                    // Update markers
                    try {
                        if (hasDriver) {
                            const driverLatLng = [dLat, dLon];
                            if (!driverMarker) {
                                const driverIcon = L.divIcon({ className: 'driver-marker', html: '<div style="background: #28a745; width: 20px; height: 20px; border-radius: 50%; border: 2px solid white;"></div>', iconSize: [28,28] });
                                driverMarker = L.marker(driverLatLng, { icon: driverIcon }).addTo(window.map).bindPopup('Driver');
                            } else { driverMarker.setLatLng(driverLatLng); }
                        }
                        if (hasPickup) {
                            const pickupLatLng = [pLat, pLon];
                            if (!pickupMarker) {
                                const pickupIcon = L.divIcon({ className: 'pickup-marker', html: '<div style="background: #ffc107; width: 20px; height: 20px; border-radius: 50%; border: 2px solid white;"></div>', iconSize: [20,20] });
                                pickupMarker = L.marker(pickupLatLng, { icon: pickupIcon }).addTo(window.map).bindPopup('Pickup');
                            } else { pickupMarker.setLatLng(pickupLatLng); }
                        }
                        if (hasDest) {
                            const destLatLng = [xLat, xLon];
                            if (!destinationMarker) {
                                const destIcon = L.divIcon({ className: 'dest-marker', html: '<div style="background: #007bff; width: 20px; height: 20px; border-radius: 50%; border: 2px solid white;"></div>', iconSize: [20,20] });
                                destinationMarker = L.marker(destLatLng, { icon: destIcon }).addTo(window.map).bindPopup('Destination');
                            } else { destinationMarker.setLatLng(destLatLng); }
                        }
                    } catch (e) { console.warn('Marker update failed', e); }

                    // Fetch routes when appropriate, but avoid repeated ORS calls if coords unchanged or rate-limited
                    let dtData = null, rdData = null;
                    try {
                        const now = Date.now();
                        const rateLimited = (_orsRateLimitedUntil && now < _orsRateLimitedUntil);
                        if (!rateLimited) {
                            if (hasDriver && hasPickup) {
                                const driverPickupKey = `${dLat},${dLon}|${pLat},${pLon}`;
                                if (driverPickupKey !== _prevDriverToPickupCoords) {
                                    const dtUrl = `https://api.openrouteservice.org/v2/directions/driving-car?api_key=${ORS_API_KEY}&start=${dLon},${dLat}&end=${pLon},${pLat}`;
                                    try {
                                        const dtRes = await fetch(dtUrl);
                                        if (dtRes.status === 429) { _orsRateLimitedUntil = now + 30000; console.warn('ORS rate limit detected (429)'); }
                                        else { dtData = await dtRes.json(); _lastDTData = dtData; _prevDriverToPickupCoords = driverPickupKey; }
                                    } catch(e) { console.warn('Driver->pickup route fetch failed', e); }
                                } else {
                                    dtData = _lastDTData;
                                }
                            }

                            if (hasPickup && hasDest) {
                                const pickupDestKey = `${pLat},${pLon}|${xLat},${xLon}`;
                                if (pickupDestKey !== _prevPickupToDestCoords) {
                                    const rdUrl = `https://api.openrouteservice.org/v2/directions/driving-car?api_key=${ORS_API_KEY}&start=${pLon},${pLat}&end=${xLon},${xLat}`;
                                    try {
                                        const rdRes = await fetch(rdUrl);
                                        if (rdRes.status === 429) { _orsRateLimitedUntil = now + 30000; console.warn('ORS rate limit detected (429)'); }
                                        else { rdData = await rdRes.json(); _lastRDData = rdData; _prevPickupToDestCoords = pickupDestKey; }
                                    } catch(e) { console.warn('Pickup->dest route fetch failed', e); }
                                } else {
                                    rdData = _lastRDData;
                                }
                            }
                        } else {
                            console.warn('Skipping ORS calls until', new Date(_orsRateLimitedUntil));
                        }
                    } catch(e) { console.warn('Route fetch failed', e); }

                    // Remove old route layers
                    try { if (driverToRiderRouteLayer) { window.map.removeLayer(driverToRiderRouteLayer); driverToRiderRouteLayer = null; } if (riderToDestRouteLayer) { window.map.removeLayer(riderToDestRouteLayer); riderToDestRouteLayer = null; } } catch(e){}

                    try {
                        if (dtData && dtData.features && dtData.features.length > 0) {
                            driverToRiderRouteLayer = L.geoJSON(dtData.features[0], { style: { color: '#28a745', weight: 5, opacity: 0.8 } }).addTo(window.map);
                        }
                        if (rdData && rdData.features && rdData.features.length > 0) {
                            riderToDestRouteLayer = L.geoJSON(rdData.features[0], { style: { color: '#007bff', weight: 5, opacity: 0.8 } }).addTo(window.map);
                        }
                    } catch(e) { console.warn('Add route failed', e); }

                    // Fit map to show layers if present
                    try {
                        const layers = [];
                        if (driverToRiderRouteLayer) layers.push(driverToRiderRouteLayer);
                        if (riderToDestRouteLayer) layers.push(riderToDestRouteLayer);
                        if (layers.length > 0) {
                            let bounds = layers[0].getBounds(); layers.forEach(l => bounds.extend(l.getBounds())); window.map.fitBounds(bounds, { padding: [50,50] });
                        }
                    } catch(e) {}

                    // Update ETA and distance UI
                    try {
                        const etaLabel = document.getElementById('eta-label'); const etaValue = document.getElementById('eta-value'); const distanceValue = document.getElementById('distance-value');
                        let etaMin = null, distKm = null;
                        if (dtData && dtData.features?.[0]?.properties?.segments?.[0]) {
                            const seg = dtData.features[0].properties.segments[0]; etaMin = Math.ceil(seg.duration/60); distKm = (seg.distance/1000).toFixed(2); etaLabel.textContent = 'Time to Pick-up:';
                        } else if (rdData && rdData.features?.[0]?.properties?.segments?.[0]) {
                            const seg = rdData.features[0].properties.segments[0]; etaMin = Math.ceil(seg.duration/60); distKm = (seg.distance/1000).toFixed(2); etaLabel.textContent = 'Time to Destination:';
                        }
                        if (etaMin != null) etaValue.textContent = `${etaMin} min`; if (distKm != null) distanceValue.textContent = `${distKm} km`;
                        // Also populate the driver-info-card summary fields if present
                        try {
                            const cardEta = document.getElementById('card-eta');
                            const cardPickup = document.getElementById('card-pickup');
                            const cardDest = document.getElementById('card-dest');
                            if (cardEta) cardEta.textContent = (etaMin != null) ? `${etaMin} min` : '--';
                            // Prefer server-provided address; fallback to booking list DOM text; last resort: coords
                            let pickupAddr = info.pickup_address || null;
                            let destAddr = info.destination_address || null;
                            if ((!pickupAddr || !destAddr) && bookingId) {
                                const bookingEl = document.querySelector(`.booking-item[data-booking-id="${bookingId}"]`);
                                if (bookingEl) {
                                    const txt = (bookingEl.textContent || '').trim();
                                    // booking item text has format: "<pickup> → <destination>"
                                    const parts = txt.split('→');
                                    if (!pickupAddr && parts[0]) pickupAddr = parts[0].trim();
                                    if (!destAddr && parts[1]) destAddr = parts[1].trim();
                                }
                            }
                            if (cardPickup) cardPickup.textContent = pickupAddr || (pLat && pLon ? `${pLat.toFixed(5)}, ${pLon.toFixed(5)}` : '--');
                            if (cardDest) cardDest.textContent = destAddr || (xLat && xLon ? `${xLat.toFixed(5)}, ${xLon.toFixed(5)}` : '--');
                        } catch(e) { /* non-critical */ }
                    } catch(e) {}

                    // Update driver info card visibility and contents
                    try {
                        const infoCard = document.getElementById('driver-info-card');
                        const bookingAccepted = (info.booking_status === 'accepted' || info.booking_status === 'on_the_way' || info.booking_status === 'started');
                        if (bookingAccepted) {
                            document.body.classList.add('booking-active');
                        } else {
                            document.body.classList.remove('booking-active');
                        }
                        if (infoCard) {
                            const previewCard = document.getElementById('booking-preview-card');
                            if (bookingAccepted) {
                                // hide the preview card when a driver has accepted (show driver info instead)
                                if (previewCard) { previewCard.style.display = 'none'; previewCard.setAttribute('aria-hidden','true'); }
                                const driverObj = info.driver || null; const tricycle = info.tricycle || {};
                                const driverName = (driverObj && driverObj.name) ? driverObj.name : (info.driver_name || 'Driver');
                                const driverPlate = (driverObj && driverObj.plate) ? driverObj.plate : (info.driver_plate || 'AB 1234');
                                const driverColor = tricycle.color || info.driver_color || 'Red';
                                infoCard.querySelector('.driver-name').textContent = driverName;
                                infoCard.querySelector('.driver-plate').textContent = `Plate: ${driverPlate}`;
                                infoCard.querySelector('.driver-color').textContent = `Color: ${driverColor}`;
                                infoCard.style.display = 'block'; infoCard.setAttribute('aria-hidden','false');
                            } else { infoCard.style.display = 'none'; infoCard.setAttribute('aria-hidden','true'); }
                            // when not accepted, ensure preview card is visible
                            if (!bookingAccepted && previewCard) { previewCard.style.display = 'block'; previewCard.setAttribute('aria-hidden','false'); }
                        }
                    } catch(e) { console.warn('Driver card update failed', e); }

                    // hide loader
                    try { if (!initialRouteLoadDone) initialRouteLoadDone = true; if (loader) { loader.classList.add('hidden'); loader.setAttribute('aria-hidden','true'); } } catch(e){}
                } catch (err) {
                    console.error('Tracking error', err);
                    const indicator = document.getElementById('status-indicator'); if (indicator) { indicator.style.backgroundColor = '#dc3545'; }
                    const loader = document.getElementById('route-loader'); if (loader) { loader.classList.add('hidden'); loader.setAttribute('aria-hidden','true'); }
                }
            }

            function startTracking(bookingId) {
                        const trackingInfo = document.getElementById('tracking-info'); if (trackingInfo) trackingInfo.style.display = 'block';
                        currentTrackedBookingId = bookingId;
                        // Ensure UI reflects that a booking is now active: hide the booking form and preview card immediately
                        try {
                            document.body.classList.add('booking-active');
                            const bookingPanel = document.querySelector('.dashboard-booking-card');
                            if (bookingPanel) bookingPanel.style.display = 'none';
                            const previewCard = document.getElementById('booking-preview-card');
                            if (previewCard) { previewCard.style.display = 'none'; previewCard.setAttribute('aria-hidden','true'); }
                            const infoCard = document.getElementById('driver-info-card');
                            if (infoCard) { infoCard.style.display = 'block'; infoCard.setAttribute('aria-hidden','false'); }
                        } catch(e) { console.warn('startTracking UI update failed', e); }

                        updateAll(bookingId);
                        if (trackingInterval) clearInterval(trackingInterval);
                        // Poll less aggressively to avoid hitting ORS rate limits; update route every 12s
                        trackingInterval = setInterval(() => updateAll(bookingId), 12000);
            }

            // Booking preview and tracking boot
            try {
                const bookingItems = document.querySelectorAll('.booking-item');
                console.debug('Booking boot: found booking items count =', bookingItems.length);
                if (bookingItems.length > 0) {
                    // find pending preview booking or first non-pending target
                    let previewBooking = null; let target = null;
                    bookingItems.forEach(el => {
                        const statusRaw = (el.querySelector('.booking-status')?.textContent || '').trim();
                        const status = statusRaw.toLowerCase();
                        const hasDriverAssigned = !!el.dataset.bookingDriver;
                        // Determine preview: pending-like statuses without a driver assigned
                        if (!previewBooking && (status.includes('pending') || status === '' ) && !hasDriverAssigned) {
                            previewBooking = el;
                        }
                        // Determine target for tracking: prefer any booking that either has a driver assigned or shows accepted/on the way/started
                        if (!target) {
                            if (hasDriverAssigned) {
                                target = el;
                            } else if (status.includes('accept') || status.includes('on the way') || status.includes('started')) {
                                target = el;
                            }
                        }
                    });

                    if (!target) target = bookingItems[0];
                    console.debug('Booking boot: previewBooking=', previewBooking, 'target=', target);

                    // If there's an accepted/on_the_way booking, start full tracking
                    if (target) {
                        const bookingStatusRaw = (target.querySelector('.booking-status')?.textContent || '').trim();
                        const bookingStatus = bookingStatusRaw.toLowerCase();
                        const bookingId = target.dataset.bookingId;
                        const hasDriverAssigned = !!target.dataset.bookingDriver;
                        // If booking indicates driver assigned or status text suggests acceptance, start tracking
                        if (bookingId && (hasDriverAssigned || bookingStatus.includes('accept') || bookingStatus.includes('on the way') || bookingStatus.includes('started') )) {
                            // hide booking panel immediately and start tracking
                            try { document.body.classList.add('booking-active'); const bookingPanel = document.querySelector('.dashboard-booking-card'); if (bookingPanel) bookingPanel.style.display = 'none'; } catch(e){}
                            startTracking(bookingId);
                        } else if (previewBooking) {
                            // show preview card
                            const bookingId = previewBooking.dataset.bookingId;
                            const pickupText = previewBooking.querySelector('strong')?.textContent?.trim() || '--';
                            const destText = previewBooking.childNodes[2]?.textContent?.trim() || '--';
                            const previewCard = document.getElementById('booking-preview-card');
                            const previewPickup = document.getElementById('preview-pickup');
                            const previewDest = document.getElementById('preview-dest');
                            const previewFare = document.getElementById('preview-fare');
                            if (previewPickup) previewPickup.textContent = pickupText; if (previewDest) previewDest.textContent = destText; if (previewFare) previewFare.textContent = 'Estimating...';
                            const previewForm = document.getElementById('preview-cancel-form'); if (previewForm) {
                                const tpl = (window.RIDER_DASH_CONFIG && window.RIDER_DASH_CONFIG.cancelBookingUrlTemplate) || previewForm.getAttribute('data-cancel-template') || previewForm.action || '';
                                if (tpl && tpl.indexOf('/0/') !== -1) {
                                    previewForm.action = tpl.replace('/0/', `/${bookingId}/`);
                                } else if (tpl) {
                                    // fallback: append id
                                    previewForm.action = tpl.replace(/\/$/, '') + `/${bookingId}/`;
                                }
                            }
                            if (previewCard) { previewCard.style.display = 'block'; previewCard.setAttribute('aria-hidden','false'); }
                            // hide booking panel
                            try { document.body.classList.add('booking-active'); const bookingPanel = document.querySelector('.dashboard-booking-card'); if (bookingPanel) bookingPanel.style.display = 'none'; } catch(e){}
                            // draw preview route once
                            try { updateAll(bookingId); } catch(e){}
                        }
                    }
                }
            } catch(e) { console.warn('Booking boot failed', e); }

            // Automatic refresh: poll booking items for status/assignment changes so rider doesn't need to refresh
            try {
                async function pollBookingItems() {
                    try {
                        const items = document.querySelectorAll('.booking-item');
                        if (!items || items.length === 0) return;
                        for (const el of items) {
                            const bid = el.dataset.bookingId;
                            if (!bid) continue;
                            try {
                                const infoRes = await fetch(`/api/booking/${bid}/route_info/`);
                                if (!infoRes.ok) continue;
                                const info = await infoRes.json();
                                if (info.status !== 'success') continue;
                                // update dataset for driver assignment
                                if (info.driver && info.driver.id) {
                                    if (!el.dataset.bookingDriver) el.dataset.bookingDriver = info.driver.id;
                                }
                                // update display text if addresses differ
                                const pickupEl = el.querySelector('strong');
                                const destText = el.childNodes[2] && el.childNodes[2].textContent ? el.childNodes[2].textContent.trim() : null;
                                if (pickupEl && info.pickup_address && pickupEl.textContent.trim() !== info.pickup_address) pickupEl.textContent = info.pickup_address;
                                if (destText && info.destination_address && destText !== info.destination_address) {
                                    // replace the arrow content after strong
                                    // simple approach: set innerHTML to pickup → destination + small est arrival if present
                                    let html = `<strong>${info.pickup_address || (pickupEl?pickupEl.textContent:'--')}</strong> → ${info.destination_address || '--'}`;
                                    if (info.estimated_arrival) html += `<br><small>Est. Arrival: ${new Date(info.estimated_arrival).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})}</small>`;
                                    el.innerHTML = html;
                                }
                                // if booking now accepted/on_the_way/started and we're not already tracking it, start tracking
                                const bookingStatus = (info.booking_status || '').toLowerCase();
                                if ((bookingStatus.includes('accept') || bookingStatus.includes('on the way') || bookingStatus.includes('started')) && (!currentTrackedBookingId || currentTrackedBookingId !== String(bid))) {
                                    // start tracking this booking
                                    try { startTracking(bid); } catch(e){}
                                }
                            } catch(e) { /* ignore per-item errors */ }
                        }
                    } catch(e) { console.warn('pollBookingItems failed', e); }
                }
                // Run immediately and then periodically (reduced frequency to lower load)
                pollBookingItems();
                setInterval(pollBookingItems, 10000);
            } catch(e) { /* non-critical */ }

            // Wire Chat button in driver-info-card to open chat for current tracked booking
            try {
                const chatBtn = document.getElementById('msg-driver-btn');
                if (chatBtn) {
                    chatBtn.addEventListener('click', (ev) => {
                        ev.preventDefault();
                        // prefer explicit currentTrackedBookingId, else fall back to any booking-item with driver
                        let bid = currentTrackedBookingId || null;
                        if (!bid) {
                            const assigned = document.querySelector('.booking-item[data-booking-driver]');
                            if (assigned) bid = assigned.dataset.bookingId;
                        }
                        if (!bid) {
                            alert('No active booking found to start chat.');
                            return;
                        }
                        if (typeof window.openChatModal === 'function') {
                            window.openChatModal(bid);
                        } else {
                            console.warn('openChatModal is not available yet');
                        }
                    });
                }
            } catch (e) { console.warn('Chat button wiring failed', e); }
})();

// Driver dashboard JS (moved from template)
(function(){
    // Ensure a placeholder exists so inline onclicks don't fail if the DOMContentLoaded handler
    // hasn't run yet or initialization is delayed. Clicks will be queued and processed later.
    if (!window.reviewBooking) {
        window._queuedReviewCalls = window._queuedReviewCalls || [];
        window.reviewBooking = function(bid) {
            console.log('reviewBooking not available yet, queuing', bid);
            window._queuedReviewCalls.push(bid);
        };
    }
    const cfg = window.DRIVER_DASH_CONFIG || {};
    const ORS_API_KEY = cfg.ORS_API_KEY || '';
    const userId = cfg.userId || null;
    const activeBookingIdFromTemplate = (cfg.activeBookingId === null) ? null : cfg.activeBookingId;

    // Helper: escape HTML
    function escapeHtml(str) {
        return String(str).replace(/[&<>"']/g, function (s) {
            return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[s];
        });
    }

    // Start active booking display (routes + ETA)
    const _activeBookingDisplays = new Set();
    function startActiveBookingDisplay(bookingId, mapInstance) {
        if (_activeBookingDisplays.has(bookingId)) return;
        try { if (window.showDriverChatButton) window.showDriverChatButton(); } catch(e){}
        _activeBookingDisplays.add(bookingId);
        const etaLabel = document.getElementById('eta-label');
        const etaValue = document.getElementById('eta-value');
        const etaSection = document.getElementById('active-trip-eta'); if (etaSection) etaSection.style.display = 'block';

    let activeDriverToRiderRouteLayer = null; let activeRiderToDestRouteLayer = null;
    let activeDriverMarker = null; let activePickupMarker = null; let activeDestMarker = null;
    let initialDriverRouteLoadDone = false;
    // local per-display ORS cache & rate-limit guard
    let _orsRateLimitedUntil = 0;
    let _prevDriverToPickupCoords = null;
    let _prevPickupToDestCoords = null;
    let _lastDTData = null;
    let _lastRDData = null;

        async function refreshEtaAndRoute() {
            try {
                const loader = document.getElementById('driver-route-loader');
                if (!initialDriverRouteLoadDone && loader) { loader.classList.remove('hidden'); loader.setAttribute('aria-hidden','false'); }
                const infoResponse = await fetch(`/api/booking/${bookingId}/route_info/`);
                const info = await infoResponse.json();
                if (!initialDriverRouteLoadDone && loader) { loader.classList.add('hidden'); loader.setAttribute('aria-hidden','true'); }
                if (info.status !== 'success') return;

                const dLat = Number(info.driver_lat), dLon = Number(info.driver_lon);
                const pLat = Number(info.pickup_lat), pLon = Number(info.pickup_lon);
                const xLat = Number(info.destination_lat), xLon = Number(info.destination_lon);

                // Only call ORS if coords changed and not currently rate-limited
                const now = Date.now();
                const rateLimited = (_orsRateLimitedUntil && now < _orsRateLimitedUntil);
                if (!rateLimited) {
                    if (Number.isFinite(dLat) && Number.isFinite(dLon) && Number.isFinite(pLat) && Number.isFinite(pLon)) {
                        const dpKey = `${dLat},${dLon}|${pLat},${pLon}`;
                        let dt = null;
                        if (dpKey !== _prevDriverToPickupCoords) {
                            const dtUrl = `https://api.openrouteservice.org/v2/directions/driving-car?api_key=${ORS_API_KEY}&start=${dLon},${dLat}&end=${pLon},${pLat}`;
                            try {
                                const dtRes = await fetch(dtUrl);
                                if (dtRes.status === 429) { _orsRateLimitedUntil = now + 30000; console.warn('ORS rate limit detected (429)'); }
                                else { dt = await dtRes.json(); _lastDTData = dt; _prevDriverToPickupCoords = dpKey; }
                            } catch(e) { console.warn('Driver->pickup route fetch failed', e); }
                        } else { dt = _lastDTData; }

                        if (dt && dt.features?.[0]?.properties?.segments?.[0]) {
                            if (activeDriverToRiderRouteLayer) mapInstance.removeLayer(activeDriverToRiderRouteLayer);
                            activeDriverToRiderRouteLayer = L.geoJSON(dt.features[0], { style: { color: '#28a745', weight: 5, opacity: 0.8 } }).addTo(mapInstance);
                            try {
                                const driverLatLng = [dLat, dLon]; const driverIcon = L.divIcon({ className: 'driver-marker', html: '<div class="marker-inner"></div>', iconSize: [30, 30] });
                                if (activeDriverMarker) activeDriverMarker.setLatLng(driverLatLng); else activeDriverMarker = L.marker(driverLatLng, { icon: driverIcon }).addTo(mapInstance).bindPopup('Driver');
                            } catch (err) { console.warn('Marker update failed', err); }
                            if (dt.features[0].properties?.segments?.[0]) {
                                const seg = dt.features[0].properties.segments[0]; if (etaValue) etaValue.textContent = `${Math.ceil(seg.duration / 60)} min`;
                            }
                        }
                    }

                    // Workaround: occasionally Leaflet tiles are clipped on load. Ensure map invalidates size after load
                    window.addEventListener('load', function () {
                        setTimeout(function () {
                            try {
                                if (window.DRIVER_MAP && typeof window.DRIVER_MAP.invalidateSize === 'function') {
                                    window.DRIVER_MAP.invalidateSize();
                                }
                                // If route layer exists, try to fit bounds so markers are visible
                                if (window.DRIVER_ROUTE_LAYER && typeof window.DRIVER_ROUTE_LAYER.getBounds === 'function' && window.DRIVER_MAP) {
                                    try {
                                        window.DRIVER_MAP.fitBounds(window.DRIVER_ROUTE_LAYER.getBounds(), { padding: [80, 80] });
                                    }
                                    catch (e) {
                                        // ignore
                                    }
                                }
                            }
                            catch (err) {
                                // ignore any errors during initial resize
                                console.warn('Driver dashboard: map invalidateSize error', err);
                            }
                        }, 300);
                    });

                    if (Number.isFinite(pLat) && Number.isFinite(pLon) && Number.isFinite(xLat) && Number.isFinite(xLon)) {
                        const pdKey = `${pLat},${pLon}|${xLat},${xLon}`;
                        let rd = null;
                        if (pdKey !== _prevPickupToDestCoords) {
                            const rdUrl = `https://api.openrouteservice.org/v2/directions/driving-car?api_key=${ORS_API_KEY}&start=${pLon},${pLat}&end=${xLon},${xLat}`;
                            try {
                                const rdRes = await fetch(rdUrl);
                                if (rdRes.status === 429) { _orsRateLimitedUntil = now + 30000; console.warn('ORS rate limit detected (429)'); }
                                else { rd = await rdRes.json(); _lastRDData = rd; _prevPickupToDestCoords = pdKey; }
                            } catch(e) { console.warn('Pickup->dest route fetch failed', e); }
                        } else { rd = _lastRDData; }

                        if (rd && rd.features?.[0]) {
                            if (activeRiderToDestRouteLayer) mapInstance.removeLayer(activeRiderToDestRouteLayer);
                            activeRiderToDestRouteLayer = L.geoJSON(rd.features[0], { style: { color: '#007bff', weight: 5, opacity: 0.8 } }).addTo(mapInstance);
                            try {
                                const pickupLatLng = [pLat, pLon]; const destLatLng = [xLat, xLon]; const pickupIcon = L.divIcon({ className: 'pickup-marker', html: '<div class="marker-inner"></div>', iconSize: [25,25] }); const destIcon = L.divIcon({ className: 'dest-marker', html: '<div class="marker-inner"></div>', iconSize: [25,25] });
                                if (activePickupMarker) activePickupMarker.setLatLng(pickupLatLng); else activePickupMarker = L.marker(pickupLatLng, { icon: pickupIcon }).addTo(mapInstance).bindPopup('Pickup Location');
                                if (activeDestMarker) activeDestMarker.setLatLng(destLatLng); else activeDestMarker = L.marker(destLatLng, { icon: destIcon }).addTo(mapInstance).bindPopup('Destination');
                            } catch (err) { console.warn('Pickup/dest marker update failed', err); }
                            // Update booking distance UI if present
                            try {
                                const seg = rd.features[0].properties?.segments?.[0];
                                if (seg) {
                                    const distEl = document.getElementById('booking-distance');
                                    if (distEl) distEl.textContent = (seg.distance/1000).toFixed(2) + ' km';
                                }
                            } catch(e) { /* ignore */ }
                        }
                    }
                } else {
                    console.warn('Skipping ORS routing due to rate limit until', new Date(_orsRateLimitedUntil));
                }

                const layers = [];
                if (activeDriverToRiderRouteLayer) layers.push(activeDriverToRiderRouteLayer);
                if (activeRiderToDestRouteLayer) layers.push(activeRiderToDestRouteLayer);
                if (layers.length > 0) { let bounds = layers[0].getBounds(); layers.forEach(l => bounds.extend(l.getBounds())); mapInstance.fitBounds(bounds, { padding: [50,50] }); }
            } catch (e) { console.error('ETA refresh error', e); } finally { initialDriverRouteLoadDone = true; try { const loader = document.getElementById('driver-route-loader'); if (loader) { loader.classList.add('hidden'); loader.setAttribute('aria-hidden','true'); } } catch(e){} }
        }
    refreshEtaAndRoute();
    // Poll less aggressively to reduce ORS calls and avoid rate limits
    setInterval(refreshEtaAndRoute, 8000);
    }

    // Driver chat modal and helpers
    (function(){
        // create modal HTML and append to body (if not present)
        if (!document.getElementById('driverChatModal')) {
            const modal = document.createElement('div'); modal.id = 'driverChatModal'; modal.style.display = 'none'; modal.style.position = 'fixed'; modal.style.right = '20px'; modal.style.bottom = '20px'; modal.style.width = '360px'; modal.style.maxWidth = '90%'; modal.style.background = '#fff'; modal.style.border = '1px solid #ccc'; modal.style.boxShadow = '0 6px 18px rgba(0,0,0,0.2)'; modal.style.zIndex = '1200'; modal.innerHTML = `
                <div style="display:flex; align-items:center; justify-content:space-between; padding:8px 12px; border-bottom:1px solid #eee; background:#f8f9fa;">
                    <strong id="driverChatTitle">Chat</strong>
                    <div><button id="driverChatClose" class="btn btn-sm">✕</button></div>
                </div>
                <div id="driverChatMessages" style="height:300px; overflow:auto; padding:12px; background:#fafafa;"><p class="muted">Loading messages...</p></div>
                <form id="driverChatForm" style="display:flex; gap:8px; padding:8px; border-top:1px solid #eee;">
                    <textarea id="driverChatInput" rows="2" style="flex:1; padding:8px;"></textarea>
                    <button type="submit" class="btn btn-primary">Send</button>
                </form>
            `; document.body.appendChild(modal);
        }

        let _driverChatBookingId = null; let _driverChatPolling = null;
        function getCookie(name) { let cookieValue = null; if (document.cookie && document.cookie !== '') { const cookies = document.cookie.split(';'); for (let i = 0; i < cookies.length; i++) { const cookie = cookies[i].trim(); if (cookie.substring(0, name.length + 1) === (name + '=')) { cookieValue = decodeURIComponent(cookie.substring(name.length + 1)); break; } } } return cookieValue; }

        async function loadDriverMessages() {
            if (!_driverChatBookingId) return; const res = await fetch(`/chat/api/booking/${_driverChatBookingId}/messages/`, { credentials: 'same-origin' }); if (!res.ok) { document.getElementById('driverChatMessages').innerHTML = '<p class="muted">Unable to load messages.</p>'; return; } const data = await res.json(); const container = document.getElementById('driverChatMessages'); container.innerHTML = ''; if (!data.messages || data.messages.length === 0) { container.innerHTML = '<p class="muted">No messages yet.</p>'; return; }
            let lastDate = null; data.messages.forEach(m => { const msgDate = new Date(m.timestamp).toDateString(); if (msgDate !== lastDate) { const sep = document.createElement('div'); sep.className = 'chat-date-sep'; sep.textContent = new Date(m.timestamp).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' }); container.appendChild(sep); lastDate = msgDate; } const div = document.createElement('div'); div.style.marginBottom = '8px'; const own = (m.sender_id == userId); div.className = own ? 'chat-msg-own' : 'chat-msg-other'; div.innerHTML = `<div class="chat-msg-meta">${m.sender_username} • ${new Date(m.timestamp).toLocaleTimeString()}</div><div>${escapeHtml(m.message)}</div>`; container.appendChild(div); });
            try { const newest = container.lastElementChild; container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' }); if (newest) { newest.classList.add('flash-animate'); setTimeout(() => newest.classList.remove('flash-animate'), 900); } } catch(e) { container.scrollTop = container.scrollHeight; }
        }

        function openDriverChatModal(bookingId) { _driverChatBookingId = bookingId; const el = document.getElementById('driverChatModal'); el.style.display = 'block'; document.getElementById('driverChatTitle').textContent = `Chat (Booking ${bookingId})`; loadDriverMessages(); _driverChatPolling = setInterval(loadDriverMessages, 3000); }
        function closeDriverChatModal() { const el = document.getElementById('driverChatModal'); el.style.display = 'none'; _driverChatBookingId = null; if (_driverChatPolling) { clearInterval(_driverChatPolling); _driverChatPolling = null; } }

        // Attach events
        document.getElementById('driverChatClose').addEventListener('click', (e) => { e.preventDefault(); closeDriverChatModal(); });
        document.getElementById('driverChatForm').addEventListener('submit', async (e) => { e.preventDefault(); if (!_driverChatBookingId) return; const txt = (document.getElementById('driverChatInput').value || '').trim(); if (!txt) return; const res = await fetch(`/chat/api/booking/${_driverChatBookingId}/messages/send/`, { method:'POST', credentials:'same-origin', headers: { 'Content-Type':'application/json','X-CSRFToken': getCookie('csrftoken') }, body: JSON.stringify({ message: txt }) }); if (!res.ok) { alert('Failed to send'); return; } document.getElementById('driverChatInput').value = ''; loadDriverMessages(); });

        // Expose open function for sidebar button
        window.openDriverChatModal = openDriverChatModal;
        window.showDriverChatButton = function() { const card = document.querySelector('.driver-booking-card'); if (card) { try { card.scrollIntoView({ behavior: 'smooth', block: 'center' }); } catch(e){} card.classList.add('pulse-highlight'); setTimeout(() => card.classList.remove('pulse-highlight'), 2400); } };
    })();

    // Map + active booking initialization
    document.addEventListener('DOMContentLoaded', function() {
        try {
            const map = L.map('map-container').setView([10.3157, 123.8854], 13);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap contributors', maxZoom: 19 }).addTo(map);
            // Leaflet needs an invalidateSize() after layout changes so the map paints full area
            setTimeout(() => { try { map.invalidateSize(); } catch(e){} }, 250);
            if (navigator.geolocation) navigator.geolocation.getCurrentPosition((pos) => { map.setView([pos.coords.latitude, pos.coords.longitude], 15); }, () => {}, { enableHighAccuracy: true, timeout: 5000 });

            let bookingId = activeBookingIdFromTemplate || document.body.getAttribute('data-active-booking-id');
            if (bookingId && bookingId !== 'null') startActiveBookingDisplay(bookingId, map);
            else {
                // initial fetch for active booking
                fetch('/api/driver/active-booking/').then(r => r.json()).then(d => { if (d.booking_id) startActiveBookingDisplay(d.booking_id, map); }).catch(()=>{});
            }

            // Expose map instance for review buttons and wire review button clicks
            window.DRIVER_MAP = map;
            // Sidebar toggles: rides icon opens the hidden sidebar-content; open-rides button also opens it
            try {
                const ridesIconEl = document.getElementById('rides-icon');
                const sidebarContentEl = document.querySelector('.sidebar-content');
                const openRidesBtn = document.getElementById('open-rides-btn');
                const ridesBack = document.getElementById('rides-back');
                if (ridesIconEl && sidebarContentEl) {
                    ridesIconEl.addEventListener('click', function(e){
                        e.preventDefault();
                    // expand the rail in-place: add a body class so CSS shifts the map
                    try { document.body.classList.add('sidebar-expanded','show-rides'); } catch(e){}
                    // show rides view inside the sidebar
                    try { const ridesView = sidebarContentEl.querySelector('.sidebar-rides'); const mainView = sidebarContentEl.querySelector('.sidebar-main'); if (ridesView && mainView) { ridesView.style.display = 'block'; mainView.style.display = 'none'; } } catch(e){}
                    try { map.invalidateSize(); } catch(e){}
                    });
                }
                if (ridesBack && sidebarContentEl) {
                    ridesBack.addEventListener('click', function(e){ e.preventDefault(); try { const ridesView = sidebarContentEl.querySelector('.sidebar-rides'); const mainView = sidebarContentEl.querySelector('.sidebar-main'); if (ridesView && mainView) { ridesView.style.display = 'none'; mainView.style.display = 'block'; } document.body.classList.remove('sidebar-expanded','show-rides'); try { map.invalidateSize(); } catch(e){} } catch(err) { console.warn('ridesBack handler', err); } });
                }
                // bottom back link (inside rides panel)
                const ridesBackBottom = document.getElementById('rides-back-bottom');
                if (ridesBackBottom && sidebarContentEl) {
                    ridesBackBottom.addEventListener('click', function(e){ e.preventDefault(); try { const ridesView = sidebarContentEl.querySelector('.sidebar-rides'); const mainView = sidebarContentEl.querySelector('.sidebar-main'); if (ridesView && mainView) { ridesView.style.display = 'none'; mainView.style.display = 'block'; } document.body.classList.remove('sidebar-expanded','show-rides'); try { map.invalidateSize(); } catch(e){} } catch(err) { console.warn('ridesBackBottom handler', err); } });
                }
                if (openRidesBtn && sidebarContentEl) {
                    openRidesBtn.addEventListener('click', function(){ try { document.body.classList.add('sidebar-expanded'); const ridesView = sidebarContentEl.querySelector('.sidebar-rides'); const mainView = sidebarContentEl.querySelector('.sidebar-main'); if (ridesView && mainView) { ridesView.style.display = 'block'; mainView.style.display = 'none'; } map.invalidateSize(); } catch(e){} });
                }
            } catch(e){ console.warn('Sidebar toggle init failed', e); }

            // Helpful debug: show console message if ORS API key missing
            if (!ORS_API_KEY || ORS_API_KEY.length < 10) {
                console.warn('OpenRouteService API key appears missing or short; client-side route preview may fail. Set OPENROUTESERVICE_API_KEY in settings and render it into DRIVER_DASH_CONFIG.');
            }
            function reviewBooking(bookingId) {
                console.log('reviewBooking called for', bookingId);
                if (!bookingId) return;
                const routeDetails = document.getElementById('route-details');
                const loader = document.getElementById('driver-route-loader');
                if (loader) { loader.classList.remove('hidden'); loader.setAttribute('aria-hidden','false'); }
                fetch(`/api/booking/${bookingId}/route_info/`).then(r => r.json()).then(async (info) => {
                    if (!info || info.status !== 'success') { console.log('route_info returned', info); if (routeDetails) routeDetails.textContent = 'No route info available.'; return; }
                    // Draw pickup->destination route for review
                    const pLat = Number(info.pickup_lat); const pLon = Number(info.pickup_lon); const xLat = Number(info.destination_lat); const xLon = Number(info.destination_lon);
                    if (!(Number.isFinite(pLat) && Number.isFinite(pLon) && Number.isFinite(xLat) && Number.isFinite(xLon))) {
                        if (routeDetails) routeDetails.textContent = 'Insufficient coordinates to preview route.'; return;
                    }
                    try {
                        console.log('ORS route request for review:', pLat,pLon,xLat,xLon);
                        // request ORS for pickup->dest
                        const rdUrl = `https://api.openrouteservice.org/v2/directions/driving-car?api_key=${ORS_API_KEY}&start=${pLon},${pLat}&end=${xLon},${xLat}`;
                        const rdRes = await fetch(rdUrl);
                        if (!rdRes.ok) { if (routeDetails) routeDetails.textContent = 'Routing service error.'; return; }
                        const rd = await rdRes.json();
                        if (rd && rd.features && rd.features[0]) {
                            console.log('ORS returned route features', rd.features[0]);
                            // remove previous review layers/markers if any
                            try { if (window._driverReviewLayer) { window.DRIVER_MAP.removeLayer(window._driverReviewLayer); window._driverReviewLayer = null; } } catch(e){}
                            try { if (window._driverReviewDriverMarker) { window.DRIVER_MAP.removeLayer(window._driverReviewDriverMarker); window._driverReviewDriverMarker = null; } } catch(e){}
                            try { if (window._driverReviewPickupMarker) { window.DRIVER_MAP.removeLayer(window._driverReviewPickupMarker); window._driverReviewPickupMarker = null; } } catch(e){}
                            try { if (window._driverReviewDestMarker) { window.DRIVER_MAP.removeLayer(window._driverReviewDestMarker); window._driverReviewDestMarker = null; } } catch(e){}


                            // add route layer (pickup->destination)
                            window._driverReviewLayer = L.geoJSON(rd.features[0], { style: { color: '#007bff', weight: 5, opacity: 0.8 } }).addTo(window.DRIVER_MAP);

                            // Additionally, draw driver -> pickup route if driver coords exist so drivers can see how far they must travel
                            try {
                                const dLat = Number(info.driver_lat); const dLon = Number(info.driver_lon);
                                if (Number.isFinite(dLat) && Number.isFinite(dLon) && Number.isFinite(pLat) && Number.isFinite(pLon)) {
                                    const dpUrl = `https://api.openrouteservice.org/v2/directions/driving-car?api_key=${ORS_API_KEY}&start=${dLon},${dLat}&end=${pLon},${pLat}`;
                                    try {
                                        const dpRes = await fetch(dpUrl);
                                        if (dpRes.ok) {
                                            const dpData = await dpRes.json();
                                            if (dpData && dpData.features && dpData.features[0]) {
                                                // remove previous driver->pickup layer if present
                                                try { if (window._driverReviewDriverToPickupLayer) { window.DRIVER_MAP.removeLayer(window._driverReviewDriverToPickupLayer); window._driverReviewDriverToPickupLayer = null; } } catch(e){}
                                                // draw solid green driver->pickup route (solid line - not dashed)
                                                window._driverReviewDriverToPickupLayer = L.geoJSON(dpData.features[0], { style: { color: '#28a745', weight: 5, opacity: 0.8 } }).addTo(window.DRIVER_MAP);
                                                try { const dpBounds = window._driverReviewDriverToPickupLayer.getBounds(); if (dpBounds) { window._driverReviewLayer.getBounds().extend(dpBounds); } } catch(e){}
                                            } else { console.log('Driver->pickup ORS returned no features', dpData); }
                                        } else {
                                            console.warn('Driver->pickup ORS request failed', dpRes.status);
                                        }
                                    } catch(e) { console.warn('Driver->pickup ORS fetch failed', e); }
                                }
                            } catch(e) { console.warn('Driver->pickup route generation failed', e); }

                            // create and add markers for driver, pickup and destination when coords are present
                            const markersToBounds = [];
                            try {
                                // driver location if available
                                const dLat = Number(info.driver_lat); const dLon = Number(info.driver_lon);
                                if (Number.isFinite(dLat) && Number.isFinite(dLon)) {
                                    const driverIcon = L.divIcon({ className: 'driver-marker', html: '<div class="marker-inner"></div>', iconSize: [28,28] });
                                    window._driverReviewDriverMarker = L.marker([dLat, dLon], { icon: driverIcon }).addTo(window.DRIVER_MAP).bindPopup('Driver');
                                    markersToBounds.push(window._driverReviewDriverMarker.getLatLng());
                                }
                                // pickup
                                if (Number.isFinite(pLat) && Number.isFinite(pLon)) {
                                    const pickupIcon = L.divIcon({ className: 'pickup-marker', html: '<div class="marker-inner"></div>', iconSize: [24,24] });
                                    window._driverReviewPickupMarker = L.marker([pLat, pLon], { icon: pickupIcon }).addTo(window.DRIVER_MAP).bindPopup('Pickup');
                                    markersToBounds.push(window._driverReviewPickupMarker.getLatLng());
                                }
                                // destination
                                if (Number.isFinite(xLat) && Number.isFinite(xLon)) {
                                    const destIcon = L.divIcon({ className: 'dest-marker', html: '<div class="marker-inner"></div>', iconSize: [24,24] });
                                    window._driverReviewDestMarker = L.marker([xLat, xLon], { icon: destIcon }).addTo(window.DRIVER_MAP).bindPopup('Destination');
                                    markersToBounds.push(window._driverReviewDestMarker.getLatLng());
                                }
                            } catch(e) { console.warn('Add review markers failed', e); }

                            // fit bounds to route layer plus markers
                            try {
                                let bounds = window._driverReviewLayer.getBounds();
                                if (markersToBounds.length > 0) { markersToBounds.forEach(ll => bounds.extend(ll)); }
                                window.DRIVER_MAP.fitBounds(bounds, { padding: [40,40] });
                            } catch(e) { console.warn('Fit bounds failed', e); }
                            // populate details
                            const seg = rd.features[0].properties?.segments?.[0];
                            if (routeDetails) routeDetails.innerHTML = `<strong>Pickup:</strong> ${info.pickup_address || '--'}<br><strong>Destination:</strong> ${info.destination_address || '--'}<br><strong>ETA:</strong> ${seg?Math.ceil(seg.duration/60)+' min':'--'} <strong>Distance:</strong> ${seg?(seg.distance/1000).toFixed(2)+' km':'--'}`;
                        } else { if (routeDetails) routeDetails.textContent = 'No route geometry returned.'; }
                    } catch (e) { console.error('Review route error', e); if (routeDetails) routeDetails.textContent = 'Error fetching route.'; }
                }).catch(e => { console.warn('Failed to fetch route_info', e); }).finally(() => { if (loader) { loader.classList.add('hidden'); loader.setAttribute('aria-hidden','true'); } });
            }

            // Expose reviewBooking globally so other scripts or delegated handlers can call it
            try {
                window.reviewBooking = reviewBooking;
                // If any clicks were queued before initialization, process them now
                if (window._queuedReviewCalls && window._queuedReviewCalls.length) {
                    const queued = window._queuedReviewCalls.slice();
                    window._queuedReviewCalls = [];
                    queued.forEach(bid => {
                        try { reviewBooking(bid); } catch(e) { console.warn('queued reviewBooking call failed', bid, e); }
                    });
                }
            } catch(e) { /* ignore */ }

            // attach click handlers to review buttons
            document.querySelectorAll('.review-ride-btn').forEach(btn => {
                btn.addEventListener('click', (ev) => {
                    ev.preventDefault(); const bid = btn.getAttribute('data-booking-id'); reviewBooking(bid);
                });
            });

            // Delegated click handler fallback: in case buttons are added later or initial binding fails
            document.addEventListener('click', function(e) {
                try {
                    const btn = e.target.closest && e.target.closest('.review-ride-btn');
                    if (!btn) return;
                    e.preventDefault(); const bid = btn.getAttribute('data-booking-id'); if (!bid) return;
                    if (typeof reviewBooking === 'function') reviewBooking(bid);
                } catch(err) { console.warn('Delegated review click handler failed', err); }
            });

            // Automatic refresh: poll for active booking changes so driver sees assignment without full page reload
            try {
                async function pollDriverActiveBooking() {
                    try {
                        const resp = await fetch('/api/driver/active-booking/');
                        if (!resp.ok) return;
                        const d = await resp.json();
                        const remoteId = d.booking_id || null;
                        const current = document.body.getAttribute('data-active-booking-id') || activeBookingIdFromTemplate || null;
                        if (remoteId && String(remoteId) !== String(current)) {
                            // update body attribute and start display
                            document.body.setAttribute('data-active-booking-id', remoteId);
                            try { startActiveBookingDisplay(remoteId, map); } catch(e) { console.warn('startActiveBookingDisplay failed', e); }
                        }
                    } catch(e) { console.warn('pollDriverActiveBooking failed', e); }
                }
                // Poll every 5 seconds
                setInterval(pollDriverActiveBooking, 5000);
            } catch(e) {}
        } catch (e) { console.warn('Driver map init failed', e); }
    });

    // Location broadcasting (moved from template) - keep minimal here; uses getCookie
    (function(){
        let locationWatchId = null; let isTracking = false;
        function getCookie(name){ let cookieValue = null; if (document.cookie && document.cookie !== '') { const cookies = document.cookie.split(';'); for (let i=0;i<cookies.length;i++){ const cookie = cookies[i].trim(); if (cookie.substring(0,name.length+1) === (name + '=')) { cookieValue = decodeURIComponent(cookie.substring(name.length+1)); break; } } } return cookieValue; }
        async function handleLocationUpdate(position) {
            const locationData = { lat: position.coords.latitude, lon: position.coords.longitude, accuracy: position.coords.accuracy, heading: position.coords.heading, speed: position.coords.speed };
            try { await fetch('/api/driver/update_location/', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') }, body: JSON.stringify(locationData) }); } catch(e) { console.error('Error updating location:', e); }
        }
        function startLocationTracking(force){ if (!navigator.geolocation) { alert('Geolocation is not supported by your browser'); return; } locationWatchId = navigator.geolocation.watchPosition(handleLocationUpdate, (err)=>console.error('loc err',err), { enableHighAccuracy:true, timeout:5000, maximumAge:0 }); isTracking = true; const activeBookingId = document.body.getAttribute('data-active-booking-id'); if (activeBookingId && force) { /* lock UI if desired */ } }
        function stopLocationTracking(){ if (locationWatchId !== null) { navigator.geolocation.clearWatch(locationWatchId); locationWatchId = null; } isTracking = false; }
        document.addEventListener('DOMContentLoaded', function(){ const activeBookingId = document.body.getAttribute('data-active-booking-id'); if (activeBookingId) { startLocationTracking(true); localStorage.setItem('driverTracking','force'); } else { if (localStorage.getItem('driverTracking') === 'true') startLocationTracking(false); } });
        window.startLocationTracking = startLocationTracking; window.stopLocationTracking = stopLocationTracking;
    })();

})();

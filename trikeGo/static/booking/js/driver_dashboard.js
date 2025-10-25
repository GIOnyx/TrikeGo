// Driver dashboard JS (moved from template)
(function(){
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

                if (Number.isFinite(dLat) && Number.isFinite(dLon) && Number.isFinite(pLat) && Number.isFinite(pLon)) {
                    const dtUrl = `https://api.openrouteservice.org/v2/directions/driving-car?api_key=${ORS_API_KEY}&start=${dLon},${dLat}&end=${pLon},${pLat}`;
                    const dtRes = await fetch(dtUrl); const dt = await dtRes.json();
                    if (dt.features?.[0]?.properties?.segments?.[0]) {
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

                if (Number.isFinite(pLat) && Number.isFinite(pLon) && Number.isFinite(xLat) && Number.isFinite(xLon)) {
                    const rdUrl = `https://api.openrouteservice.org/v2/directions/driving-car?api_key=${ORS_API_KEY}&start=${pLon},${pLat}&end=${xLon},${xLat}`;
                    const rdRes = await fetch(rdUrl); const rd = await rdRes.json();
                    if (rd.features?.[0]) {
                        if (activeRiderToDestRouteLayer) mapInstance.removeLayer(activeRiderToDestRouteLayer);
                        activeRiderToDestRouteLayer = L.geoJSON(rd.features[0], { style: { color: '#007bff', weight: 5, opacity: 0.8 } }).addTo(mapInstance);
                        try {
                            const pickupLatLng = [pLat, pLon]; const destLatLng = [xLat, xLon]; const pickupIcon = L.divIcon({ className: 'pickup-marker', html: '<div class="marker-inner"></div>', iconSize: [25,25] }); const destIcon = L.divIcon({ className: 'dest-marker', html: '<div class="marker-inner"></div>', iconSize: [25,25] });
                            if (activePickupMarker) activePickupMarker.setLatLng(pickupLatLng); else activePickupMarker = L.marker(pickupLatLng, { icon: pickupIcon }).addTo(mapInstance).bindPopup('Pickup Location');
                            if (activeDestMarker) activeDestMarker.setLatLng(destLatLng); else activeDestMarker = L.marker(destLatLng, { icon: destIcon }).addTo(mapInstance).bindPopup('Destination');
                        } catch (err) { console.warn('Pickup/dest marker update failed', err); }
                    }
                }

                const layers = [];
                if (activeDriverToRiderRouteLayer) layers.push(activeDriverToRiderRouteLayer);
                if (activeRiderToDestRouteLayer) layers.push(activeRiderToDestRouteLayer);
                if (layers.length > 0) { let bounds = layers[0].getBounds(); layers.forEach(l => bounds.extend(l.getBounds())); mapInstance.fitBounds(bounds, { padding: [50,50] }); }
            } catch (e) { console.error('ETA refresh error', e); } finally { initialDriverRouteLoadDone = true; try { const loader = document.getElementById('driver-route-loader'); if (loader) { loader.classList.add('hidden'); loader.setAttribute('aria-hidden','true'); } } catch(e){} }
        }
        refreshEtaAndRoute(); setInterval(refreshEtaAndRoute, 5000);
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
            if (navigator.geolocation) navigator.geolocation.getCurrentPosition((pos) => { map.setView([pos.coords.latitude, pos.coords.longitude], 15); }, () => {}, { enableHighAccuracy: true, timeout: 5000 });

            let bookingId = activeBookingIdFromTemplate || document.body.getAttribute('data-active-booking-id');
            if (bookingId && bookingId !== 'null') startActiveBookingDisplay(bookingId, map);
            else {
                fetch('/api/driver/active-booking/').then(r => r.json()).then(d => { if (d.booking_id) startActiveBookingDisplay(d.booking_id, map); }).catch(()=>{});
            }
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

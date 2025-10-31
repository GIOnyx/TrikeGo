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
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Helper: escape HTML
    function escapeHtml(str) {
        return String(str).replace(/[&<>"']/g, function (s) {
            return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[s];
        });
    }

    // ---- Multi-stop itinerary state management ----
    let itineraryData = null;
    let currentStopIndex = 0;
    let itineraryExpanded = false;
    let itineraryTimer = null;
    let itineraryMarkers = [];
    let itineraryRouteLayer = null;
    let itineraryRouteSignature = null;
    let itineraryRouteIsFallback = false;
    let itineraryRouteRequestId = 0;
    let itineraryRoutePaneCache = {};
    let itineraryDom = {};
    let mapInstance = null;
    let routeLoaderDepth = 0;
    let itineraryHasLoaded = false;

    function updateRouteLoaderVisibility() {
        const loaderEl = document.getElementById('driver-route-loader');
        if (!loaderEl) {
            return;
        }
        if (routeLoaderDepth > 0) {
            loaderEl.classList.remove('hidden');
            loaderEl.setAttribute('aria-hidden', 'false');
        } else {
            loaderEl.classList.add('hidden');
            loaderEl.setAttribute('aria-hidden', 'true');
        }
    }

    function showRouteLoader() {
        routeLoaderDepth += 1;
        updateRouteLoaderVisibility();
    }

    function hideRouteLoader() {
        if (routeLoaderDepth > 0) {
            routeLoaderDepth -= 1;
            updateRouteLoaderVisibility();
        }
    }

    function getTripBookingIds() {
        if (!itineraryData || !Array.isArray(itineraryData.stops)) return [];
        const idSet = new Set();
        itineraryData.stops.forEach(stop => {
            if (stop && stop.bookingId) {
                idSet.add(stop.bookingId);
            }
        });
        return Array.from(idSet);
    }

    function getPreferredChatBookingId() {
        const bookingIds = getTripBookingIds();
        if (!bookingIds.length) {
            return null;
        }
        if (itineraryData && Array.isArray(itineraryData.stops) && itineraryData.stops[currentStopIndex]) {
            return itineraryData.stops[currentStopIndex].bookingId || bookingIds[0];
        }
        return bookingIds[0];
    }

    function updateTrackingState() {
        const hasStops = itineraryData && Array.isArray(itineraryData.stops) && itineraryData.stops.length > 0;
        if (hasStops) {
            document.body.setAttribute('data-has-itinerary', 'true');
            if (typeof window.startLocationTracking === 'function') {
                window.startLocationTracking(false);
            }
        } else {
            document.body.removeAttribute('data-has-itinerary');
            if (typeof window.stopLocationTracking === 'function') {
                window.stopLocationTracking();
            }
        }
    }

    function initItinerary(map) {
        mapInstance = map;
        itineraryRoutePaneCache = {};
        itineraryDom = {
            card: document.getElementById('itinerary-card'),
            summaryStatusText: document.getElementById('summary-status-text'),
            summaryActionType: document.getElementById('summary-action-type'),
            summaryAddress: document.getElementById('summary-address'),
            summaryActionBtn: document.getElementById('summary-action-btn'),
            summaryStopNum: document.getElementById('summary-stop-num'),
            summaryStopTotal: document.getElementById('summary-stop-total'),
            expandBtn: document.getElementById('itinerary-expand-btn'),
            collapseBtn: document.getElementById('itinerary-collapse-btn'),
            fullBookingCount: document.getElementById('full-booking-count'),
            fullCapacity: document.getElementById('full-capacity'),
            fullEarnings: document.getElementById('full-earnings'),
            stopList: document.getElementById('itinerary-stop-list'),
            summaryContainer: document.getElementById('itinerary-summary'),
            fullContainer: document.getElementById('itinerary-full'),
            chatBtn: document.getElementById('open-chat-btn'),
        };

        if (!itineraryDom.card) {
            return;
        }

        itineraryExpanded = false;
        itineraryDom.card.classList.add('collapsed');

        if (itineraryDom.expandBtn) {
            itineraryDom.expandBtn.addEventListener('click', () => toggleItinerary(true));
        }
        if (itineraryDom.collapseBtn) {
            itineraryDom.collapseBtn.addEventListener('click', () => toggleItinerary(false));
        }
        if (itineraryDom.summaryActionBtn) {
            itineraryDom.summaryActionBtn.addEventListener('click', handleSummaryActionClick);
        }
        if (itineraryDom.chatBtn) {
            itineraryDom.chatBtn.addEventListener('click', openTripChatFromUI);
        }

        fetchItineraryData();
        itineraryTimer = setInterval(fetchItineraryData, 12000);
    }

    function toggleItinerary(expand) {
        if (!itineraryDom.card) return;
        itineraryExpanded = !!expand;
        itineraryDom.card.classList.toggle('expanded', itineraryExpanded);
        itineraryDom.card.classList.toggle('collapsed', !itineraryExpanded);
        if (itineraryDom.fullContainer) {
            itineraryDom.fullContainer.style.display = itineraryExpanded ? 'block' : 'none';
        }
    }

    function clearItineraryMarkers() {
        if (!mapInstance) return;
        itineraryMarkers.forEach(marker => {
            try { mapInstance.removeLayer(marker); } catch (err) { /* ignore */ }
        });
        itineraryMarkers = [];
    }

    function resetItineraryRoute() {
        if (!mapInstance) {
            itineraryRouteLayer = null;
            itineraryRouteSignature = null;
            return;
        }
        if (itineraryRouteLayer && mapInstance.hasLayer(itineraryRouteLayer)) {
            try { mapInstance.removeLayer(itineraryRouteLayer); } catch (err) { /* ignore */ }
        }
        itineraryRouteLayer = null;
        itineraryRouteSignature = null;
        itineraryRouteIsFallback = false;
    }

    function clearItineraryMapLayers() {
        clearItineraryMarkers();
        resetItineraryRoute();
    }

    function getStopActionLabel(stop) {
        if (!stop) return 'Proceed';
        if (stop.type === 'PICKUP') {
            return stop.status === 'CURRENT' ? 'Start Pickup' : 'Queue Pickup';
        }
        return stop.status === 'CURRENT' ? 'Confirm Drop-off' : 'Queue Drop-off';
    }

    function buildStopStatusClass(status) {
        if (status === 'COMPLETED') return 'completed';
        if (status === 'CURRENT') return 'current';
        return 'pending';
    }

    function formatStatusLabel(status) {
        switch ((status || 'UPCOMING').toUpperCase()) {
            case 'COMPLETED':
                return 'Completed';
            case 'CURRENT':
                return 'Current';
            default:
                return 'Upcoming';
        }
    }

    function renderStopList(stops) {
        if (!itineraryDom.stopList) return;
        itineraryDom.stopList.innerHTML = '';

        const fragment = document.createDocumentFragment();
        stops.forEach((stop, index) => {
            const li = document.createElement('li');
            li.className = `stop-item ${buildStopStatusClass(stop.status)}`;

            const typeLabel = stop.type === 'PICKUP' ? 'Pick Up' : 'Drop Off';
            const badgeClass = stop.type === 'PICKUP' ? '' : 'dropoff';
            const statusClass = stop.status ? stop.status.toLowerCase() : 'upcoming';
            const statusLabel = formatStatusLabel(stop.status);
            const passengerLabel = stop.passengerCount === 1 ? '1 passenger' : `${stop.passengerCount} passengers`;

            li.innerHTML = `
                <div class="stop-header">
                    <div>
                        <span class="stop-badge ${badgeClass}">${index + 1}</span>
                        ${escapeHtml(typeLabel)} &ndash; ${escapeHtml(stop.passengerName || 'Passenger')}
                    </div>
                    <span class="stop-status-pill ${escapeHtml(statusClass)}">${escapeHtml(statusLabel)}</span>
                </div>
                <div class="stop-meta">${escapeHtml(stop.address || '--')}</div>
                <div class="stop-meta">${escapeHtml(passengerLabel)}</div>
                ${stop.note ? `<div class="stop-note">${escapeHtml(stop.note)}</div>` : ''}
            `;

            fragment.appendChild(li);
        });

        itineraryDom.stopList.appendChild(fragment);
    }

    function buildItineraryRoutePoints(itinerary) {
        const points = [];
        const pushPoint = (lat, lon) => {
            const latNum = Number(lat);
            const lonNum = Number(lon);
            if (!Number.isFinite(latNum) || !Number.isFinite(lonNum)) return;
            if (points.length > 0) {
                const [prevLat, prevLon] = points[points.length - 1];
                if (Math.abs(prevLat - latNum) < 1e-5 && Math.abs(prevLon - lonNum) < 1e-5) {
                    return;
                }
            }
            points.push([latNum, lonNum]);
        };

        if (Array.isArray(itinerary?.fullRoutePolyline) && itinerary.fullRoutePolyline.length >= 2) {
            itinerary.fullRoutePolyline.forEach(pt => {
                if (Array.isArray(pt) && pt.length >= 2) {
                    pushPoint(pt[0], pt[1]);
                }
            });
        }

        if (points.length < 2 && Array.isArray(itinerary?.stops)) {
            itinerary.stops.forEach(stop => {
                if (!Array.isArray(stop.coordinates) || stop.coordinates.length !== 2) return;
                pushPoint(stop.coordinates[0], stop.coordinates[1]);
            });
        }

        return points;
    }

    async function requestORSRouteFeature(points) {
        const coordPairs = points.map(([lat, lon]) => {
            const latNum = Number(lat);
            const lonNum = Number(lon);
            if (!Number.isFinite(latNum) || !Number.isFinite(lonNum)) return null;
            return [lonNum, latNum];
        }).filter(Boolean);

        if (coordPairs.length < 2) {
            return null;
        }

        try {
            const response = await fetch('https://api.openrouteservice.org/v2/directions/driving-car', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': ORS_API_KEY,
                },
                body: JSON.stringify({ coordinates: coordPairs, instructions: false }),
            });

            if (!response.ok) {
                let errText = '';
                try { errText = await response.text(); } catch (e) {/* noop */}
                console.warn('ORS route request failed', response.status, errText);
                return null;
            }

            const data = await response.json();
            if (data && data.features && data.features[0]) {
                return data.features[0];
            }
        } catch (err) {
            console.warn('ORS route request error', err);
        }

        return null;
    }

    const ROUTE_COLORS = {
        PICKUP: '#0b63d6',
        DROPOFF: '#0b63d6'
    };

    function ensureRoutePane(paneName, zIndex) {
        if (!mapInstance || !paneName) {
            return null;
        }

        if (!itineraryRoutePaneCache[paneName]) {
            let pane = mapInstance.getPane(paneName);
            if (!pane) {
                pane = mapInstance.createPane(paneName);
            }
            if (pane) {
                if (typeof zIndex === 'number') {
                    pane.style.zIndex = String(zIndex);
                }
                pane.style.pointerEvents = 'none';
            }
            itineraryRoutePaneCache[paneName] = paneName;
        }

        return paneName;
    }

    function buildSegmentLayer(segments) {
        if (!mapInstance) return null;
        if (!Array.isArray(segments) || segments.length === 0) return null;

        const pickupPane = ensureRoutePane('itinerary-route-pickup', 370);
        const dropoffPane = ensureRoutePane('itinerary-route-dropoff', 360);
        const group = L.layerGroup();
        segments.forEach(segment => {
            const rawPoints = Array.isArray(segment?.points) ? segment.points : [];
            const points = rawPoints.map(pt => {
                if (!Array.isArray(pt) || pt.length < 2) return null;
                const lat = Number(pt[0]);
                const lon = Number(pt[1]);
                if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null;
                return [lat, lon];
            }).filter(Boolean);

            if (points.length < 2) {
                return;
            }

            const typeKey = (segment?.type || '').toUpperCase();
            const color = ROUTE_COLORS[typeKey] || ROUTE_COLORS.PICKUP;
            const precise = Boolean(segment?.precise);
            const style = precise
                ? { color, weight: 5, opacity: 0.88 }
                : { color, weight: 4, opacity: 0.6, dashArray: '6 8' };

            const paneName = typeKey === 'DROPOFF' ? dropoffPane : pickupPane;
            const layer = L.polyline(points, { ...style, pane: paneName });
            group.addLayer(layer);
            if (typeKey === 'PICKUP' && typeof layer.bringToFront === 'function') {
                layer.bringToFront();
            }
        });

        if (group.getLayers().length === 0) {
            return null;
        }

        group.addTo(mapInstance);
        return group;
    }

    async function ensureItineraryRouteLayer(itinerary) {
        if (!mapInstance) return null;

        const points = buildItineraryRoutePoints(itinerary);
        if (points.length < 2) {
            resetItineraryRoute();
            return null;
        }

        const signature = points.map(pt => `${pt[0].toFixed(5)},${pt[1].toFixed(5)}`).join('|');
        const hasApiKey = ORS_API_KEY && ORS_API_KEY.length > 10;
        const routeSegments = Array.isArray(itinerary?.fullRouteSegments) ? itinerary.fullRouteSegments : [];
        const hasSegmentGeometry = routeSegments.some(seg => Array.isArray(seg?.points) && seg.points.length >= 2);
        const hasServerPreciseRoute = Boolean(itinerary && itinerary.fullRouteIsPrecise && hasSegmentGeometry);
        const shouldRequestORS = hasApiKey && !hasServerPreciseRoute;

        if (itineraryRouteLayer && itineraryRouteSignature === signature) {
            const layerIsUsable = !itineraryRouteIsFallback || !shouldRequestORS;
            if (layerIsUsable) {
                if (!mapInstance.hasLayer(itineraryRouteLayer)) {
                    mapInstance.addLayer(itineraryRouteLayer);
                }
                return typeof itineraryRouteLayer.getBounds === 'function' ? itineraryRouteLayer.getBounds() : null;
            }
        }

        let loaderShown = false;
        const ensureLoader = () => {
            if (!loaderShown) {
                showRouteLoader();
                loaderShown = true;
            }
        };
        const cleanupLoader = () => {
            if (loaderShown) {
                hideRouteLoader();
                loaderShown = false;
            }
        };

        itineraryRouteRequestId += 1;
        const requestId = itineraryRouteRequestId;
        ensureLoader();

        if (itineraryRouteLayer && mapInstance.hasLayer(itineraryRouteLayer)) {
            try { mapInstance.removeLayer(itineraryRouteLayer); } catch (err) { /* ignore */ }
        }
        itineraryRouteLayer = null;

        try {
            let newLayer = null;
            if (hasSegmentGeometry) {
                newLayer = buildSegmentLayer(routeSegments);
                itineraryRouteIsFallback = !Boolean(itinerary?.fullRouteIsPrecise);
            }

            if (shouldRequestORS) {
                const feature = await requestORSRouteFeature(points);
                if (requestId !== itineraryRouteRequestId) {
                    return null;
                }
                if (feature) {
                    if (newLayer && mapInstance.hasLayer(newLayer)) {
                        try { mapInstance.removeLayer(newLayer); } catch (err) { /* ignore */ }
                    }
                    const paneName = ensureRoutePane('itinerary-route-ors', 365);
                    newLayer = L.geoJSON(feature, {
                        style: { color: '#0b63d6', weight: 5, opacity: 0.88 },
                        pane: paneName
                    }).addTo(mapInstance);
                    itineraryRouteIsFallback = false;
                }
            }

            if (!newLayer) {
                const baseStyle = { color: '#0b63d6', weight: 5, opacity: 0.88 };
                const fallbackStyle = { ...baseStyle, weight: 4, opacity: 0.7, dashArray: '6 8' };
                const lineStyle = hasServerPreciseRoute ? baseStyle : fallbackStyle;
                const paneName = ensureRoutePane('itinerary-route-fallback', 355);
                newLayer = L.polyline(points.map(([lat, lon]) => [lat, lon]), { ...lineStyle, pane: paneName }).addTo(mapInstance);
                itineraryRouteIsFallback = !hasServerPreciseRoute;

                if (hasSegmentGeometry && itinerary?.fullRouteIsPrecise) {
                    newLayer.setStyle(baseStyle);
                }
            }

            itineraryRouteLayer = newLayer;
            itineraryRouteSignature = signature;

            return typeof newLayer.getBounds === 'function' ? newLayer.getBounds() : null;
        } catch (err) {
            console.warn('Unable to render itinerary route', err);
            itineraryRouteLayer = null;
            itineraryRouteSignature = null;
            itineraryRouteIsFallback = false;
            return null;
        } finally {
            cleanupLoader();
        }
    }

    async function renderItineraryMap(itinerary) {
        if (!mapInstance) return;

        try {
            clearItineraryMarkers();

            if (!itinerary || !Array.isArray(itinerary.stops) || itinerary.stops.length === 0) {
                resetItineraryRoute();
                return;
            }

            const boundsPoints = [];

            const driverCoord = Array.isArray(itinerary.driverStartCoordinate) ? itinerary.driverStartCoordinate : null;
            if (driverCoord && driverCoord.length === 2) {
                const driverLat = Number(driverCoord[0]);
                const driverLon = Number(driverCoord[1]);
                if (Number.isFinite(driverLat) && Number.isFinite(driverLon)) {
                    const driverIcon = L.divIcon({
                        className: 'driver-marker stop-marker',
                        html: '<div class="marker-inner"></div>',
                        iconSize: [32, 36],
                        iconAnchor: [16, 36],
                    });
                    const driverMarker = L.marker([driverLat, driverLon], { icon: driverIcon }).addTo(mapInstance);
                    driverMarker.bindPopup('Driver start location');
                    itineraryMarkers.push(driverMarker);
                    boundsPoints.push([driverLat, driverLon]);
                }
            }

            itinerary.stops.forEach((stop, idx) => {
                if (!Array.isArray(stop.coordinates) || stop.coordinates.length !== 2) return;
                const lat = Number(stop.coordinates[0]);
                const lon = Number(stop.coordinates[1]);
                if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;

                const isPickup = (stop.type || '').toUpperCase() === 'PICKUP';
                const iconClass = isPickup
                    ? 'pickup-marker marker-pickup'
                    : 'dest-marker marker-dropoff';
                const markerHtml = `<div class="marker-inner"><div class="marker-label">${idx + 1}</div></div>`;
                const icon = L.divIcon({
                    className: `stop-sequence-marker stop-marker ${iconClass}`,
                    html: markerHtml,
                    iconSize: [30, 36],
                    iconAnchor: [15, 36],
                });
                const markerTitle = isPickup ? 'Pickup' : 'Drop-off';
                const marker = L.marker([lat, lon], { icon }).addTo(mapInstance);
                marker.bindPopup(`${markerTitle}<br>${escapeHtml(stop.address || '--')}`);
                itineraryMarkers.push(marker);
                boundsPoints.push([lat, lon]);
                if (stop.status === 'CURRENT') {
                    marker.openPopup();
                }
            });

            const routeBounds = await ensureItineraryRouteLayer(itinerary);
            let combinedBounds = null;

            if (routeBounds) {
                if (typeof routeBounds.isValid === 'function' && !routeBounds.isValid()) {
                    combinedBounds = null;
                } else {
                    combinedBounds = typeof routeBounds.clone === 'function' ? routeBounds.clone() : routeBounds;
                }
            }

            // Ensure markers render above route layers so they remain visible.
            try {
                itineraryMarkers.forEach(marker => {
                    try {
                        if (marker && typeof marker.setZIndexOffset === 'function') marker.setZIndexOffset(1000);
                        if (marker && typeof marker.bringToFront === 'function') marker.bringToFront();
                    } catch (e) { /* ignore individual marker errors */ }
                });
            } catch (e) { /* ignore */ }

            boundsPoints.forEach(([lat, lon]) => {
                if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
                const point = L.latLng(lat, lon);
                if (!combinedBounds) {
                    combinedBounds = L.latLngBounds(point, point);
                } else {
                    combinedBounds.extend(point);
                }
            });

            if (combinedBounds && typeof combinedBounds.isValid === 'function' ? combinedBounds.isValid() : true) {
                try {
                    mapInstance.fitBounds(combinedBounds, { padding: [60, 60], maxZoom: 17 });
                } catch (err) {
                    console.warn('fitBounds failed', err);
                }
            }
        } catch (err) {
            console.warn('renderItineraryMap failed', err);
        }
    }

    function renderItineraryUI() {
        if (!itineraryDom.summaryStatusText || !itineraryData) {
            if (itineraryDom.summaryStatusText) itineraryDom.summaryStatusText.textContent = 'NO ITINERARY';
            if (itineraryDom.summaryActionBtn) {
                itineraryDom.summaryActionBtn.textContent = 'Start';
                itineraryDom.summaryActionBtn.disabled = true;
            }
            if (itineraryDom.summaryActionType) itineraryDom.summaryActionType.textContent = '--';
            if (itineraryDom.summaryAddress) itineraryDom.summaryAddress.textContent = 'Awaiting assignments.';
            if (itineraryDom.fullBookingCount) itineraryDom.fullBookingCount.textContent = '0';
            if (itineraryDom.fullCapacity) itineraryDom.fullCapacity.textContent = '0 / 0';
            if (itineraryDom.fullEarnings) itineraryDom.fullEarnings.textContent = '0.00';
            if (itineraryDom.summaryStopNum) itineraryDom.summaryStopNum.textContent = '0';
            if (itineraryDom.summaryStopTotal) itineraryDom.summaryStopTotal.textContent = '0';
            if (itineraryDom.chatBtn) {
                itineraryDom.chatBtn.disabled = true;
                itineraryDom.chatBtn.removeAttribute('data-chat-booking-id');
            }
            renderStopList([]);
            clearItineraryMapLayers();
            return;
        }

        const stops = Array.isArray(itineraryData.stops) ? itineraryData.stops : [];
        if (stops.length === 0) {
            itineraryDom.summaryStatusText.textContent = 'NO ITINERARY';
            itineraryDom.summaryActionType.textContent = '--';
            itineraryDom.summaryAddress.textContent = 'Awaiting assignments.';
            itineraryDom.summaryActionBtn.disabled = true;
            itineraryDom.summaryActionBtn.textContent = 'Start';
            itineraryDom.summaryActionBtn.removeAttribute('data-stop-id');
            if (itineraryDom.fullBookingCount) itineraryDom.fullBookingCount.textContent = '0';
            if (itineraryDom.fullCapacity) itineraryDom.fullCapacity.textContent = `${itineraryData.currentCapacity || 0} / ${itineraryData.maxCapacity || 0}`;
            if (itineraryDom.fullEarnings) itineraryDom.fullEarnings.textContent = (itineraryData.totalEarnings || 0).toFixed(2);
            if (itineraryDom.summaryStopNum) itineraryDom.summaryStopNum.textContent = '0';
            if (itineraryDom.summaryStopTotal) itineraryDom.summaryStopTotal.textContent = '0';
            if (itineraryDom.chatBtn) {
                itineraryDom.chatBtn.disabled = true;
                itineraryDom.chatBtn.removeAttribute('data-chat-booking-id');
            }
            renderStopList([]);
            clearItineraryMapLayers();
            return;
        }

        currentStopIndex = Math.min(Math.max(Number(itineraryData.currentStopIndex || 0), 0), stops.length - 1);
        const currentStop = stops[currentStopIndex];

        itineraryDom.summaryStatusText.textContent = 'UP NEXT';
        const actionPrefix = currentStop.type === 'PICKUP' ? 'PICK UP' : 'DROP OFF';
        const passengerName = currentStop.passengerName || 'Passenger';
        const passengerSuffix = currentStop.passengerCount > 1 ? ` (+${currentStop.passengerCount})` : ' (+1)';
        itineraryDom.summaryActionType.textContent = `${actionPrefix}: ${passengerName}${passengerSuffix}`;
        itineraryDom.summaryAddress.textContent = currentStop.address || '--';
        itineraryDom.summaryActionBtn.disabled = false;
        itineraryDom.summaryActionBtn.textContent = getStopActionLabel(currentStop);
        itineraryDom.summaryActionBtn.setAttribute('data-stop-id', currentStop.stopId);

        if (itineraryDom.summaryStopNum) itineraryDom.summaryStopNum.textContent = String(currentStopIndex + 1);
        if (itineraryDom.summaryStopTotal) itineraryDom.summaryStopTotal.textContent = String(stops.length);

        if (itineraryDom.fullBookingCount) itineraryDom.fullBookingCount.textContent = String(itineraryData.totalBookings || 0);
        if (itineraryDom.fullCapacity) itineraryDom.fullCapacity.textContent = `${itineraryData.currentCapacity || 0} / ${itineraryData.maxCapacity || 0}`;
        if (itineraryDom.fullEarnings) itineraryDom.fullEarnings.textContent = (itineraryData.totalEarnings || 0).toFixed(2);

        if (itineraryDom.chatBtn) {
            const chatBookingId = getPreferredChatBookingId();
            if (chatBookingId) {
                itineraryDom.chatBtn.disabled = false;
                itineraryDom.chatBtn.setAttribute('data-chat-booking-id', String(chatBookingId));
            } else {
                itineraryDom.chatBtn.disabled = true;
                itineraryDom.chatBtn.removeAttribute('data-chat-booking-id');
            }
        }

        renderStopList(stops);
        renderItineraryMap(itineraryData);
    }

    async function fetchItineraryData() {
        if (!cfg.itineraryEndpoint) return;
        const showLoaderDuringFetch = !itineraryHasLoaded;
        if (showLoaderDuringFetch) {
            showRouteLoader();
        }
        try {
            const response = await fetch(cfg.itineraryEndpoint, { credentials: 'same-origin' });
            if (!response.ok) {
                throw new Error(`Status ${response.status}`);
            }
            const payload = await response.json();
            if (!payload || payload.status !== 'success') {
                throw new Error('Invalid itinerary payload');
            }
            itineraryData = payload.itinerary || null;
            updateTrackingState();
            renderItineraryUI();
            if (!itineraryHasLoaded) {
                itineraryHasLoaded = true;
            }
        } catch (err) {
            console.warn('Failed to fetch itinerary', err);
        } finally {
            if (showLoaderDuringFetch) {
                hideRouteLoader();
            }
        }
    }

    async function completeItineraryStop(stopId) {
        if (!cfg.completeStopEndpoint || !stopId) return;
        try {
            const csrf = cfg.csrfToken || getCookie('csrftoken');
            const response = await fetch(cfg.completeStopEndpoint, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrf,
                },
                body: JSON.stringify({ stopId })
            });

            if (!response.ok) {
                const text = await response.text();
                throw new Error(text || response.statusText);
            }

            const payload = await response.json();
            if (payload && payload.itinerary) {
                itineraryData = payload.itinerary;
                updateTrackingState();
                renderItineraryUI();
            } else {
                fetchItineraryData();
            }
        } catch (err) {
            console.warn('Failed to complete stop', err);
            alert('Unable to update stop. Please try again.');
        }
    }

    function handleSummaryActionClick() {
        if (!itineraryDom.summaryActionBtn || !itineraryData) return;
        const stopId = itineraryDom.summaryActionBtn.getAttribute('data-stop-id');
        if (!stopId) return;
        itineraryDom.summaryActionBtn.disabled = true;
        completeItineraryStop(stopId).finally(() => {
            itineraryDom.summaryActionBtn.disabled = false;
        });
    }

    function openTripChatFromUI(event) {
        if (event) {
            event.preventDefault();
        }
        const preferredIdAttr = itineraryDom.chatBtn ? itineraryDom.chatBtn.getAttribute('data-chat-booking-id') : null;
        const parsedId = preferredIdAttr ? Number(preferredIdAttr) : NaN;
        const bookingId = Number.isFinite(parsedId) ? parsedId : getPreferredChatBookingId();
        if (typeof window.openDriverChatModal === 'function') {
            window.openDriverChatModal(bookingId);
        }
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
            if (!_driverChatBookingId) {
                return;
            }

            const container = document.getElementById('driverChatMessages');
            let response;
            try {
                response = await fetch(`/chat/api/booking/${_driverChatBookingId}/messages/`, { credentials: 'same-origin' });
            } catch (fetchErr) {
                container.innerHTML = '<p class="muted">Unable to load messages.</p>';
                return;
            }

            if (!response.ok) {
                container.innerHTML = '<p class="muted">Unable to load messages.</p>';
                return;
            }

            let payload;
            try {
                payload = await response.json();
            } catch (parseErr) {
                container.innerHTML = '<p class="muted">Unable to load messages.</p>';
                return;
            }

            const messages = Array.isArray(payload.messages) ? payload.messages : [];
            if (!messages.length) {
                container.innerHTML = '<p class="muted">No messages yet.</p>';
                const titleEl = document.getElementById('driverChatTitle');
                if (titleEl) titleEl.textContent = 'Trip Chat';
                return;
            }

            const bookingIds = new Set();
            messages.forEach(msg => {
                if (msg && msg.booking_id) {
                    bookingIds.add(msg.booking_id);
                }
            });

            container.innerHTML = '';
            let lastDate = null;
            messages.forEach(msg => {
                const timestamp = new Date(msg.timestamp);
                const dateKey = timestamp.toDateString();
                if (dateKey !== lastDate) {
                    const sep = document.createElement('div');
                    sep.className = 'chat-date-sep';
                    sep.textContent = timestamp.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
                    container.appendChild(sep);
                    lastDate = dateKey;
                }

                const div = document.createElement('div');
                div.style.marginBottom = '8px';
                const own = Number(msg.sender_id) === Number(userId);
                div.className = own ? 'chat-msg-own' : 'chat-msg-other';

                const senderName = escapeHtml(msg.sender_display_name || msg.sender_username || 'Participant');
                const senderRole = msg.sender_role ? ` • ${escapeHtml(msg.sender_role)}` : '';
                const timeLabel = timestamp.toLocaleTimeString();
                const showBookingContext = bookingIds.size > 1;
                const bookingLabel = showBookingContext ? `<div class="chat-msg-booking">${escapeHtml(msg.booking_label || `Booking ${msg.booking_id}`)}</div>` : '';

                div.innerHTML = `
                    <div class="chat-msg-meta">${senderName}${senderRole} • ${timeLabel}</div>
                    ${bookingLabel}
                    <div>${escapeHtml(msg.message)}</div>
                `;
                container.appendChild(div);
            });

            try {
                const newest = container.lastElementChild;
                container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
                if (newest) {
                    newest.classList.add('flash-animate');
                    setTimeout(() => newest.classList.remove('flash-animate'), 900);
                }
            } catch (e) {
                container.scrollTop = container.scrollHeight;
            }

            const titleEl = document.getElementById('driverChatTitle');
            if (titleEl) {
                titleEl.textContent = bookingIds.size > 1 ? `Trip Chat (${bookingIds.size} bookings)` : 'Trip Chat';
            }
        }

        function openDriverChatModal(bookingId) {
            const normalizedId = Number.isFinite(Number(bookingId)) ? Number(bookingId) : null;
            _driverChatBookingId = normalizedId || getPreferredChatBookingId();
            if (!_driverChatBookingId) {
                alert('No active bookings to chat with yet.');
                return;
            }
            const el = document.getElementById('driverChatModal');
            el.style.display = 'block';
            const titleEl = document.getElementById('driverChatTitle');
            if (titleEl) {
                titleEl.textContent = 'Trip Chat';
            }
            loadDriverMessages();
            _driverChatPolling = setInterval(loadDriverMessages, 6000);
        }

        function closeDriverChatModal() {
            const el = document.getElementById('driverChatModal');
            el.style.display = 'none';
            _driverChatBookingId = null;
            if (_driverChatPolling) {
                clearInterval(_driverChatPolling);
                _driverChatPolling = null;
            }
        }

        // Attach events
        document.getElementById('driverChatClose').addEventListener('click', (e) => { e.preventDefault(); closeDriverChatModal(); });
        document.getElementById('driverChatForm').addEventListener('submit', async (e) => { e.preventDefault(); if (!_driverChatBookingId) return; const txt = (document.getElementById('driverChatInput').value || '').trim(); if (!txt) return; const res = await fetch(`/chat/api/booking/${_driverChatBookingId}/messages/send/`, { method:'POST', credentials:'same-origin', headers: { 'Content-Type':'application/json','X-CSRFToken': getCookie('csrftoken') }, body: JSON.stringify({ message: txt }) }); if (!res.ok) { alert('Failed to send'); return; } document.getElementById('driverChatInput').value = ''; loadDriverMessages(); });

        // Expose open function for sidebar button
        window.openDriverChatModal = openDriverChatModal;
        window.showDriverChatButton = function() {
            const card = document.getElementById('itinerary-card');
            if (card) {
                try { card.scrollIntoView({ behavior: 'smooth', block: 'center' }); } catch (e) { /* ignore */ }
                card.classList.add('pulse-highlight');
                setTimeout(() => card.classList.remove('pulse-highlight'), 2400);
            }
        };
    })();

    // Map + active booking initialization
    document.addEventListener('DOMContentLoaded', function() {
        try {
            const map = L.map('map-container').setView([10.3157, 123.8854], 13);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap contributors', maxZoom: 19 }).addTo(map);
            // Leaflet needs an invalidateSize() after layout changes so the map paints full area
            setTimeout(() => { try { map.invalidateSize(); } catch(e){} }, 250);
            if (navigator.geolocation) navigator.geolocation.getCurrentPosition((pos) => { map.setView([pos.coords.latitude, pos.coords.longitude], 15); }, () => {}, { enableHighAccuracy: true, timeout: 5000 });

            // Expose map instance for review buttons and wire review button clicks
            window.DRIVER_MAP = map;
            initItinerary(map);
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
                let loaderShown = false;
                const ensureLoader = () => {
                    if (!loaderShown) {
                        showRouteLoader();
                        loaderShown = true;
                    }
                };
                const finalizeLoader = () => {
                    if (loaderShown) {
                        hideRouteLoader();
                        loaderShown = false;
                    }
                };
                ensureLoader();

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
                                                window._driverReviewDriverToPickupLayer = L.geoJSON(dpData.features[0], { style: { color: '#0b63d6', weight: 5, opacity: 0.8 } }).addTo(window.DRIVER_MAP);
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
                }).catch(e => { console.warn('Failed to fetch route_info', e); }).finally(finalizeLoader);
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

            // Intercept accept ride form submissions and perform AJAX POST to avoid accidental delegation
            document.querySelectorAll('form.accept-ride-form').forEach(form => {
                form.addEventListener('submit', async function(e) {
                    e.preventDefault();
                    try {
                        const bid = form.getAttribute('data-booking-id');
                        const submitBtn = form.querySelector('button[type="submit"]');
                        if (submitBtn) submitBtn.disabled = true;
                        // CSRF token: prefer global config then fallback to cookie
                        const csrf = (cfg && cfg.csrfToken) ? cfg.csrfToken : (function(){ let name='csrftoken'; let v=null; if (document.cookie && document.cookie!=='') { const cookies=document.cookie.split(';'); for(let i=0;i<cookies.length;i++){ const c=cookies[i].trim(); if (c.substring(0,name.length+1)===(name+'=')){ v=decodeURIComponent(c.substring(name.length+1)); break; } } } return v; })();
                        const resp = await fetch(form.action, { method: 'POST', credentials: 'same-origin', headers: { 'X-CSRFToken': csrf }, body: new URLSearchParams(new FormData(form)) });
                        if (!resp.ok) {
                            // On failure, re-enable button and show a basic alert
                            if (submitBtn) submitBtn.disabled = false;
                            const txt = await resp.text();
                            alert('Accept failed: ' + (txt || resp.statusText));
                            return;
                        }
                        // On success, server redirects to driver dashboard; just reload to refresh UI
                        // But we also attempt to start active booking display quickly if booking id available
                        try { const data = await resp.clone().text(); } catch(e){}
                        // small delay to allow server-side to settle then reload
                        setTimeout(() => { try { window.location.reload(); } catch(e){ location.reload(); } }, 300);
                    } catch (err) {
                        console.warn('Accept request failed', err);
                        try { const submitBtn = form.querySelector('button[type="submit"]'); if (submitBtn) submitBtn.disabled = false; } catch(e){}
                        alert('Network error while accepting ride.');
                    }
                });
            });

            // Cancel booking handler: use fetch POST to avoid nested form issues
            document.addEventListener('click', function(e) {
                try {
                    const cb = e.target.closest && e.target.closest('#cancel-booking-btn');
                    if (!cb) return;
                    e.preventDefault();
                    const url = cb.getAttribute('data-cancel-url');
                    if (!url) { alert('Cancel URL missing'); return; }
                    // simple getCookie utility
                    function getCookie(name){ let cookieValue = null; if (document.cookie && document.cookie !== '') { const cookies = document.cookie.split(';'); for (let i=0;i<cookies.length;i++){ const cookie = cookies[i].trim(); if (cookie.substring(0, name.length+1) === (name + '=')) { cookieValue = decodeURIComponent(cookie.substring(name.length+1)); break; } } } return cookieValue; }
                    const csrf = getCookie('csrftoken');
                    cb.disabled = true;
                    fetch(url, { method: 'POST', credentials: 'same-origin', headers: { 'X-CSRFToken': csrf } }).then(res => {
                        if (res.ok) {
                            // reload to refresh UI
                            window.location.reload();
                        } else {
                            cb.disabled = false;
                            res.text().then(t => { alert('Cancel failed: ' + (t || res.statusText)); });
                        }
                    }).catch(err => { cb.disabled = false; alert('Network error when cancelling'); console.warn(err); });
                } catch(err) { console.warn('cancel handler', err); }
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
        function startLocationTracking(force){
            if (!navigator.geolocation) { alert('Geolocation is not supported by your browser'); return; }
            if (isTracking && !force) { return; }
            if (locationWatchId !== null) {
                navigator.geolocation.clearWatch(locationWatchId);
                locationWatchId = null;
            }
            locationWatchId = navigator.geolocation.watchPosition(handleLocationUpdate, (err)=>console.error('loc err',err), { enableHighAccuracy:true, timeout:5000, maximumAge:0 });
            isTracking = true;
            localStorage.setItem('driverTracking', force ? 'force' : 'true');
        }
    function stopLocationTracking(){ if (locationWatchId !== null) { navigator.geolocation.clearWatch(locationWatchId); locationWatchId = null; } isTracking = false; localStorage.removeItem('driverTracking'); }
        document.addEventListener('DOMContentLoaded', function(){
            const hasItinerary = document.body.getAttribute('data-has-itinerary') === 'true';
            if (hasItinerary) {
                startLocationTracking(true);
            } else if (localStorage.getItem('driverTracking') === 'true') {
                startLocationTracking(false);
            }
        });
        window.startLocationTracking = startLocationTracking; window.stopLocationTracking = stopLocationTracking;
    })();

})();

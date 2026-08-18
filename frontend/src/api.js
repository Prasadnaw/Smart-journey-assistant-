// Production backend on Render.
// For local development, Vite can still proxy /api requests if VITE_API_BASE
// is not set.
const BASE = 'https://smart-journey-assistant-1-web.onrender.com'
  import.meta.env.VITE_API_BASE ||
  (import.meta.env.DEV ? '' : 'https://smart-journey-assistant.onrender.com')

async function request(path, options = {}) {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })

  if (!res.ok) {
    let detail = `Request failed (${res.status})`

    try {
      const body = await res.json()
      detail = body.detail || detail
    } catch (e) {
      // Ignore JSON parse failure.
    }

    throw new Error(detail)
  }

  return res.json()
}

export const api = {
  status: () => request('/api/status'),

  locationSearch: (q) =>
    request(`/api/location-search?q=${encodeURIComponent(q)}`),

  reverseGeocode: (lat, lon) =>
    request(`/api/geocode?lat=${lat}&lon=${lon}`),

  weather: (lat, lon) =>
    request(`/api/weather?lat=${lat}&lon=${lon}`),

  cityPlaces: (lat, lon, limit = 8) =>
    request(`/api/city-places?lat=${lat}&lon=${lon}&limit=${limit}`),

  localFood: (lat, lon, limit = 9) =>
    request(`/api/local-food?lat=${lat}&lon=${lon}&limit=${limit}`),

  roadRoute: (fromLat, fromLon, toLat, toLon, mode = 'taxi') =>
    request(
      `/api/road-route?from_lat=${fromLat}&from_lon=${fromLon}&to_lat=${toLat}&to_lon=${toLon}&mode=${mode}`
    ),

  transitStops: (lat, lon, radiusM = 800) =>
    request(
      `/api/transit-stops?lat=${lat}&lon=${lon}&radius_m=${radiusM}`
    ),

  searchJourneys: (payload) =>
    request('/api/journeys/search', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getJourney: (id) =>
    request(`/api/journeys/${id}`),
}

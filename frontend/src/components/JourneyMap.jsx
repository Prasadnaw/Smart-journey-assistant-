import { MapContainer, TileLayer, Marker, Polyline, Popup, useMap } from 'react-leaflet'
import { useEffect, useRef } from 'react'
import L from 'leaflet'

// Default Leaflet marker icons don't load correctly under Vite bundling
// unless we point them at the CDN explicitly.
const defaultIcon = new L.Icon({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
})

const MODE_COLORS = {
  walk: '#64748b', cycle: '#22c55e', bus: '#f59e0b', metro: '#2563eb',
  train: '#7c3aed', taxi: '#ef4444', change: '#94a3b8',
}

/**
 * Leaflet measures its container's pixel size the moment it mounts. If
 * that container is inside a conditionally-rendered / flex / animated
 * layout, it can still be 0px wide (or its old width) at that instant --
 * Leaflet then renders tiles for the wrong box, which shows up as the map
 * looking squeezed into the left side with grey space on the right.
 *
 * Fixing this needs two things:
 *  1. map.invalidateSize() after the container has its real, final size.
 *  2. Re-running fitBounds() *after* that invalidation, not before --
 *     otherwise the center/zoom Leaflet computes is based on the stale
 *     (wrong) box size too.
 *
 * A ResizeObserver keeps this correct if the window or layout resizes
 * later (e.g. opening/closing filters, switching between desktop and
 * mobile).
 */
function MapSizeFix({ bounds }) {
  const map = useMap()
  const containerRef = useRef(null)

  useEffect(() => {
    containerRef.current = map.getContainer()

    const fix = () => {
      map.invalidateSize()
      if (bounds && bounds.length > 0) {
        map.fitBounds(bounds, { padding: [40, 40] })
      }
    }

    // Run once after layout settles (covers the initial mount case).
    const raf = requestAnimationFrame(() => setTimeout(fix, 60))

    // Keep it correct if the container is resized later.
    const observer = new ResizeObserver(() => fix())
    if (containerRef.current) observer.observe(containerRef.current)

    return () => {
      cancelAnimationFrame(raf)
      observer.disconnect()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, JSON.stringify(bounds)])

  return null
}

export default function JourneyMap({ origin, destination, segments = [], transitStops = [] }) {
  if (!origin || !destination) return null

  const allPoints = [[origin.latitude, origin.longitude], [destination.latitude, destination.longitude]]
  segments.forEach((s) => {
    if (s.polyline) s.polyline.forEach((p) => allPoints.push(p))
  })

  return (
    <div className="journey-map-wrap">
      <MapContainer
        center={allPoints[0]}
        zoom={12}
        className="journey-map"
        scrollWheelZoom
        preferCanvas
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <MapSizeFix bounds={allPoints} />

        <Marker position={[origin.latitude, origin.longitude]} icon={defaultIcon}>
          <Popup>Start: {origin.raw_label || origin.name}</Popup>
        </Marker>
        <Marker position={[destination.latitude, destination.longitude]} icon={defaultIcon}>
          <Popup>Destination: {destination.raw_label || destination.name}</Popup>
        </Marker>

        {segments.map((s, idx) =>
          s.polyline && s.polyline.length > 1 ? (
            <Polyline
              key={idx}
              positions={s.polyline}
              pathOptions={{ color: MODE_COLORS[s.mode] || '#2563eb', weight: 5, opacity: 0.85 }}
            />
          ) : null
        )}

        {transitStops.map((stop, idx) => (
          <Marker key={idx} position={[stop.latitude, stop.longitude]} icon={defaultIcon}>
            <Popup>{stop.name} ({stop.kind})</Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  )
}


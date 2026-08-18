export default function LiveContext({ origin, destination, weather, roadDistanceKm, transitAvailable, loading }) {
  if (loading) {
    return <div className="live-context loading">Gathering live context…</div>
  }

  return (
    <div className="live-context">
      <h3>Live context</h3>
      <div className="live-context-grid">
        <div className="live-context-item">
          <div className="live-context-icon">📍</div>
          <div>
            <div className="live-context-label">Locations</div>
            <div className="live-context-value">
              {origin?.raw_label || origin?.name} → {destination?.raw_label || destination?.name}
            </div>
          </div>
        </div>

        <div className="live-context-item">
          <div className="live-context-icon">🛣</div>
          <div>
            <div className="live-context-label">Road distance</div>
            <div className="live-context-value">
              {roadDistanceKm != null ? `${roadDistanceKm} km` : 'Unavailable'}
            </div>
          </div>
        </div>

        <div className="live-context-item">
          <div className="live-context-icon">🌦</div>
          <div>
            <div className="live-context-label">Weather at destination</div>
            <div className="live-context-value">
              {weather ? `${Math.round(weather.temperature_c)}°C, ${weather.condition}` : 'Unavailable'}
            </div>
          </div>
        </div>

        <div className="live-context-item">
          <div className="live-context-icon">🚌</div>
          <div>
            <div className="live-context-label">Transit availability</div>
            <div className="live-context-value">
              {transitAvailable ? 'Live/scheduled data found' : 'Estimated routes only'}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

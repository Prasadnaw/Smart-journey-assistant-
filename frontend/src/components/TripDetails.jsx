import JourneyLeg, { DataBadge } from './JourneyLeg'

function formatDuration(min) {
  const totalMin = Math.round(min)
  const d = Math.floor(totalMin / 1440)
  const h = Math.floor((totalMin % 1440) / 60)
  const m = totalMin % 60
  const parts = []
  if (d > 0) parts.push(`${d}d`)
  if (h > 0) parts.push(`${h}h`)
  if (m > 0 || parts.length === 0) parts.push(`${m}m`)
  return parts.join(' ')
}

export default function TripDetails({ journey }) {
  if (!journey) return null

  const walkingKm = journey.total_walking_meters / 1000
  const transportMinutes = journey.segments
    .filter((s) => s.mode !== 'change')
    .reduce((sum, s) => sum + s.duration_minutes, 0)
  const waitingMinutes = journey.segments
    .filter((s) => s.mode === 'change')
    .reduce((sum, s) => sum + s.duration_minutes, 0)

  return (
    <div className="trip-details">
      <div className="trip-details-header">
        <div className="trip-route">
          <span>{journey.origin}</span>
          <span className="trip-route-arrow">↓</span>
          <span>{journey.destination}</span>
        </div>
        <div className="trip-summary-stats">
          <span className="trip-summary-time">{formatDuration(journey.total_duration_minutes)}</span>
          <span>₹{Math.round(journey.total_fare_inr)} <DataBadge source={journey.fare_source} /></span>
          <span>{journey.num_changes} change{journey.num_changes === 1 ? '' : 's'}</span>
          <span>{journey.total_walking_meters >= 1000 ? `${walkingKm.toFixed(1)} km` : `${Math.round(journey.total_walking_meters)} m`} walking</span>
        </div>
      </div>

      <div className="trip-breakdown">
        <div className="breakdown-item">
          <div className="breakdown-icon">💰</div>
          <div>
            <div className="breakdown-label">Fare</div>
            <div className="breakdown-value">₹{Math.round(journey.total_fare_inr)} <DataBadge source={journey.fare_source} /></div>
          </div>
        </div>
        <div className="breakdown-item">
          <div className="breakdown-icon">🚶</div>
          <div>
            <div className="breakdown-label">Walking</div>
            <div className="breakdown-value">
              {journey.total_walking_meters >= 1000 ? `${walkingKm.toFixed(1)} km` : `${Math.round(journey.total_walking_meters)} m`}
            </div>
          </div>
        </div>
        <div className="breakdown-item">
          <div className="breakdown-icon">🔄</div>
          <div>
            <div className="breakdown-label">Changes</div>
            <div className="breakdown-value">{journey.num_changes}</div>
          </div>
        </div>
        <div className="breakdown-item">
          <div className="breakdown-icon">⏱</div>
          <div>
            <div className="breakdown-label">Travel</div>
            <div className="breakdown-value">{formatDuration(transportMinutes)}</div>
          </div>
        </div>
        <div className="breakdown-item">
          <div className="breakdown-icon">⏳</div>
          <div>
            <div className="breakdown-label">Waiting</div>
            <div className="breakdown-value">{formatDuration(waitingMinutes)}</div>
          </div>
        </div>
        <div className="breakdown-item">
          <div className="breakdown-icon">🌱</div>
          <div>
            <div className="breakdown-label">CO₂</div>
            <div className="breakdown-value">
              {journey.co2_grams >= 1000 ? `${(journey.co2_grams / 1000).toFixed(1)} kg` : `${journey.co2_grams} g`}
            </div>
          </div>
        </div>
        <div className="breakdown-item">
          <div className="breakdown-icon">✓</div>
          <div>
            <div className="breakdown-label">Reliability</div>
            <div className="breakdown-value">{journey.reliability_pct}% <DataBadge source={journey.time_source} /></div>
          </div>
        </div>
      </div>

      <h3 className="step-by-step-title">Step-by-step</h3>
      <div className="step-by-step">
        <div className="step-marker">📍 Start — {journey.origin}</div>
        {journey.segments.map((s, idx) => (
          <div key={idx} className="step-wrapper">
            <div className="step-connector">↓</div>
            <JourneyLeg segment={s} />
          </div>
        ))}
        <div className="step-connector">↓</div>
        <div className="step-marker">🏁 Destination — {journey.destination}</div>
      </div>
    </div>
  )
}

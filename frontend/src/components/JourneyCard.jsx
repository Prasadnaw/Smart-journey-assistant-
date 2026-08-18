import { useNavigate } from 'react-router-dom'
import { DataBadge } from './JourneyLeg'

const MODE_ICONS = {
  walk: '🚶', cycle: '🚲', bus: '🚌', metro: '🚇', train: '🚆', taxi: '🚕', change: '🔄',
}

const TAG_LABELS = {
  best_match: 'BEST MATCH', fastest: 'FASTEST', cheapest: 'CHEAPEST',
  fewest_changes: 'FEWEST CHANGES', least_walking: 'LEAST WALKING', greenest: 'GREENEST',
}

function formatDuration(min) {
  const h = Math.floor(min / 60)
  const m = Math.round(min % 60)
  return h > 0 ? `${h}h ${m}m` : `${m}m`
}

export default function JourneyCard({ journey }) {
  const navigate = useNavigate()

  return (
    <button type="button" className="journey-card" onClick={() => navigate(`/trip/${journey.id}`)}>
      {journey.tags?.length > 0 && (
        <div className="journey-card-tags">
          {journey.tags.slice(0, 2).map((tag) => (
            <span key={tag} className={`journey-tag journey-tag-${tag}`}>{TAG_LABELS[tag] || tag}</span>
          ))}
        </div>
      )}

      <div className="journey-card-top">
        <div className="journey-card-time">{formatDuration(journey.total_duration_minutes)}</div>
        <div className="journey-card-fare">
          ₹{Math.round(journey.total_fare_inr)} <DataBadge source={journey.fare_source} />
        </div>
      </div>

      <div className="journey-card-stats">
        <span>🔄 {journey.num_changes} change{journey.num_changes === 1 ? '' : 's'}</span>
        <span>🚶 {journey.total_walking_meters >= 1000
          ? `${(journey.total_walking_meters / 1000).toFixed(1)} km`
          : `${Math.round(journey.total_walking_meters)} m`}</span>
        <span>🌱 {journey.co2_grams >= 1000 ? `${(journey.co2_grams / 1000).toFixed(1)} kg` : `${journey.co2_grams} g`} CO₂</span>
        <span>✓ {journey.reliability_pct}% reliability</span>
      </div>

      <div className="journey-card-route">
        {journey.segments
          .filter((s) => s.mode !== 'change')
          .map((s, idx, arr) => (
            <span key={idx} className="route-step">
              {MODE_ICONS[s.mode] || '➡️'}
              {idx < arr.length - 1 && <span className="route-arrow">→</span>}
            </span>
          ))}
      </div>
    </button>
  )
}

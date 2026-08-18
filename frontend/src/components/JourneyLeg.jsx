const MODE_ICONS = {
  walk: '🚶', cycle: '🚲', bus: '🚌', metro: '🚇', train: '🚆', taxi: '🚕', change: '🔄',
}

const SOURCE_LABELS = {
  official: 'Official', live: 'Live', scheduled: 'Scheduled', estimated: 'Estimated', unknown: 'Unknown',
}

export function DataBadge({ source }) {
  if (!source) return null
  return <span className={`data-badge data-badge-${source}`}>{SOURCE_LABELS[source] || source}</span>
}

export default function JourneyLeg({ segment, compact }) {
  const icon = MODE_ICONS[segment.mode] || '➡️'
  const isChange = segment.mode === 'change'

  if (isChange) {
    return (
      <div className="leg leg-change">
        <span className="leg-icon">{icon}</span>
        <span className="leg-text">
          Change at <strong>{segment.from_location}</strong> — {Math.round(segment.duration_minutes)} min wait
        </span>
      </div>
    )
  }

  return (
    <div className="leg">
      <span className="leg-icon">{icon}</span>
      <div className="leg-body">
        <div className="leg-headline">
          <span className="leg-mode">{segment.mode.charAt(0).toUpperCase() + segment.mode.slice(1)}</span>
          {segment.line_name && <span className="leg-line">{segment.line_name}</span>}
          {segment.train_number && <span className="leg-train-no">#{segment.train_number}</span>}
        </div>
        {!compact && (
          <div className="leg-route">
            {segment.from_location} → {segment.to_location}
          </div>
        )}
        <div className="leg-meta">
          <span>{Math.round(segment.duration_minutes)} min</span>
          {segment.distance_meters != null && (
            <span>
              {segment.distance_meters >= 1000
                ? `${(segment.distance_meters / 1000).toFixed(1)} km`
                : `${Math.round(segment.distance_meters)} m`}
            </span>
          )}
          {segment.fare_inr != null && segment.fare_inr > 0 && (
            <span>
              ₹{Math.round(segment.fare_inr)} <DataBadge source={segment.fare_source} />
            </span>
          )}
          <DataBadge source={segment.time_source} />
        </div>
      </div>
    </div>
  )
}

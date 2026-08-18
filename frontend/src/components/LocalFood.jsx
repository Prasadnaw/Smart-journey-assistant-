const KIND_ICONS = { restaurant: '🍽️', cafe: '☕', fast_food: '🥡' }

export default function LocalFood({ spots, cityName, loading }) {
  if (loading) {
    return <div className="local-food loading">Finding places to eat…</div>
  }
  if (!spots || spots.length === 0) return null

  return (
    <div className="local-food">
      <h3>Food & drink near {cityName || 'your destination'}</h3>
      <p className="local-food-sub">Real nearby spots from OpenStreetMap — not a curated "best of" list.</p>
      <div className="local-food-grid">
        {spots.map((spot, idx) => (
          <div key={idx} className="food-chip">
            <span className="food-chip-icon">{KIND_ICONS[spot.kind] || '🍴'}</span>
            <div>
              <div className="food-chip-name">{spot.name}</div>
              {spot.cuisine && <div className="food-chip-cuisine">{spot.cuisine}</div>}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

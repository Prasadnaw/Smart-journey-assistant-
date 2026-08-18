const PLACEHOLDER = '/place-placeholder.svg'

function PlaceImage({ src, name }) {
  return (
    <img
      src={src || PLACEHOLDER}
      alt={name}
      loading="lazy"
      onError={(event) => {
        if (event.currentTarget.src.endsWith(PLACEHOLDER)) return
        event.currentTarget.src = PLACEHOLDER
      }}
    />
  )
}

export default function FamousPlaces({ places, cityName, loading }) {
  if (loading) {
    return (
      <div className="famous-places loading">
        Loading places to explore…
      </div>
    )
  }

  if (!places || places.length === 0) return null

  return (
    <div className="famous-places">
      <div className="section-kicker">DESTINATION DISCOVERY</div>

      <h3>Explore {cityName || 'your destination'}</h3>

      <p className="section-subtitle">
        Landmarks, attractions and places worth knowing before you arrive.
      </p>

      <div className="famous-places-grid">
        {places.map((place, idx) => (
          <a
            key={`${place.name}-${idx}`}
            className="place-card"
            href={place.source_url || '#'}
            target="_blank"
            rel="noopener noreferrer"
          >
            <div className="place-card-image">
              <PlaceImage
                src={place.image_url}
                name={place.name}
              />
            </div>

            <div className="place-card-body">
              <div className="place-card-name">
                {place.name}
              </div>

              {place.description && (
                <div className="place-card-desc">
                  {place.description}
                </div>
              )}

              {place.source_url && (
                <div className="place-card-source">
                  Source: Wikipedia
                </div>
              )}
            </div>
          </a>
        ))}
      </div>
    </div>
  )
}
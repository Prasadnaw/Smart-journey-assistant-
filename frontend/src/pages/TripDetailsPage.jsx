import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Header from '../components/Header'
import JourneyMap from '../components/JourneyMap'
import TripDetails from '../components/TripDetails'
import { api } from '../api'

export default function TripDetailsPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [journey, setJourney] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let mounted = true
    setLoading(true)
    api.getJourney(id)
      .then((j) => mounted && setJourney(j))
      .catch((err) => mounted && setError(err.message || 'This journey could not be found.'))
      .finally(() => mounted && setLoading(false))
    return () => { mounted = false }
  }, [id])

  // We only have the journey's segment labels here (not the original
  // Location objects), so build minimal origin/destination points from the
  // first/last segment coordinates when available for the map.
  const originPoint = journey?.segments?.[0]?.polyline?.[0]
  const destPoint = journey?.segments?.[journey.segments.length - 1]?.polyline?.slice(-1)?.[0]

  return (
    <div className="page">
      <Header />
      <div className="trip-page-content">
        <button type="button" className="back-btn" onClick={() => navigate(-1)}>← Back to results</button>

        {loading && <div className="loading">Loading journey…</div>}
        {error && <div className="search-error">{error}</div>}

        {journey && (
          <>
            <h1 className="trip-page-title">Journey details</h1>
            {originPoint && destPoint && (
              <JourneyMap
                origin={{ latitude: originPoint[0], longitude: originPoint[1], name: journey.origin, raw_label: journey.origin }}
                destination={{ latitude: destPoint[0], longitude: destPoint[1], name: journey.destination, raw_label: journey.destination }}
                segments={journey.segments}
              />
            )}
            <TripDetails journey={journey} />
          </>
        )}
      </div>
    </div>
  )
}

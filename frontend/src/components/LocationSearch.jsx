import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import CurrentLocationButton from './CurrentLocationButton'

const POPULAR_CITIES = [
  'Mumbai', 'Delhi', 'Bengaluru', 'Chennai', 'Hyderabad', 'Kolkata', 'Pune',
  'Ahmedabad', 'Jaipur', 'Lucknow', 'Kochi', 'Chandigarh', 'Nagpur', 'Indore',
  'Bhopal', 'Coimbatore', 'Visakhapatnam', 'Surat', 'Nashik',
]

const FEATURE_ICONS = {
  city: '🏙️', locality: '📍', address: '🏠', railway_station: '🚉',
  metro_station: '🚇', bus_stop: '🚌', airport: '✈️', landmark: '🗺️',
  tourist_place: '🎡', unknown: '📍',
}

export default function LocationSearch({ label, placeholder, value, onChange, allowCurrentLocation }) {
  const [query, setQuery] = useState(value?.raw_label || value?.name || '')
  const [results, setResults] = useState([])
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')
  const debounceRef = useRef(null)
  const containerRef = useRef(null)

  useEffect(() => {
    setQuery(value?.raw_label || value?.name || '')
  }, [value])

  useEffect(() => {
    function handleClickOutside(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleInputChange = (e) => {
    const q = e.target.value
    setQuery(q)
    setErrorMsg('')
    if (debounceRef.current) clearTimeout(debounceRef.current)

    if (q.trim().length < 2) {
      setResults([])
      setOpen(q.trim().length > 0)
      return
    }

    debounceRef.current = setTimeout(async () => {
      setLoading(true)
      try {
        const res = await api.locationSearch(q)
        setResults(res)
        setOpen(true)
      } catch (err) {
        setErrorMsg('Search is temporarily unavailable — please try again.')
        setResults([])
      } finally {
        setLoading(false)
      }
    }, 350)
  }

  const selectLocation = (loc) => {
    onChange(loc)
    setQuery(loc.raw_label || loc.name)
    setOpen(false)
  }

  const selectCity = async (cityName) => {
    setLoading(true)
    setOpen(true)
    try {
      const res = await api.locationSearch(cityName)
      if (res.length > 0) {
        selectLocation(res[0])
      } else {
        setErrorMsg(`Could not find "${cityName}" right now.`)
      }
    } catch {
      setErrorMsg('Search is temporarily unavailable — please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="location-search" ref={containerRef}>
      <label className="location-label">{label}</label>
      <input
        className="location-input"
        type="text"
        placeholder={placeholder}
        value={query}
        onChange={handleInputChange}
        onFocus={() => query.trim().length > 0 && setOpen(true)}
      />

      {allowCurrentLocation && (
        <CurrentLocationButton onLocated={(loc) => selectLocation(loc)} />
      )}

      {open && (
        <div className="location-dropdown">
          {loading && <div className="location-dropdown-status">Searching…</div>}
          {errorMsg && <div className="location-dropdown-status error">{errorMsg}</div>}

          {!loading && results.length === 0 && query.trim().length >= 2 && !errorMsg && (
            <div className="location-dropdown-status">No matches found.</div>
          )}

          {results.map((loc, idx) => (
            <button
              type="button"
              key={`${loc.name}-${loc.latitude}-${loc.longitude}-${idx}`}
              className="location-result"
              onClick={() => selectLocation(loc)}
            >
              <span className="location-result-icon">{FEATURE_ICONS[loc.feature_type] || '📍'}</span>
              <span className="location-result-text">
                <span className="location-result-name">{loc.name}</span>
                <span className="location-result-sub">
                  {[loc.locality, loc.state].filter((p) => p && p !== loc.name).join(', ') || loc.country}
                </span>
              </span>
            </button>
          ))}

          {query.trim().length < 2 && (
            <div className="popular-cities">
              <div className="location-dropdown-status">Popular cities</div>
              <div className="popular-cities-grid">
                {POPULAR_CITIES.map((city) => (
                  <button type="button" key={city} className="popular-city-chip" onClick={() => selectCity(city)}>
                    {city}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

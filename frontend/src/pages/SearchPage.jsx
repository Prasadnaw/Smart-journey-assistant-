import { useState } from 'react'
import Header from '../components/Header'
import LocationSearch from '../components/LocationSearch'
import TransportFilters, { PrioritySelector } from '../components/TransportFilters'
import FilterPanel from '../components/FilterPanel'
import JourneyCard from '../components/JourneyCard'
import LiveContext from '../components/LiveContext'
import FamousPlaces from '../components/FamousPlaces'
import LocalFood from '../components/LocalFood'
import JourneyMap from '../components/JourneyMap'
import ApiStatus from '../components/ApiStatus'
import { api } from '../api'

const DEFAULT_MODES = ['train', 'metro', 'bus', 'walk', 'taxi']

export default function SearchPage() {
  const [origin, setOrigin] = useState(null)
  const [destination, setDestination] = useState(null)
  const [priority, setPriority] = useState('general')
  const [modes, setModes] = useState(DEFAULT_MODES)
  const [filters, setFilters] = useState({})
  const [showFilters, setShowFilters] = useState(false)

  const [searching, setSearching] = useState(false)
  const [searchError, setSearchError] = useState('')
  const [result, setResult] = useState(null)

  const [contextLoading, setContextLoading] = useState(false)
  const [weather, setWeather] = useState(null)
  const [places, setPlaces] = useState(null)
  const [food, setFood] = useState(null)

  const canSearch = origin && destination

  const handleSearch = async () => {
    if (!canSearch) return
    setSearching(true)
    setSearchError('')
    setResult(null)
    setContextLoading(true)
    setWeather(null)
    setPlaces(null)
    setFood(null)

    const payload = {
      origin,
      destination,
      priority,
      modes,
      max_fare_inr: filters.max_fare_inr ?? null,
      max_duration_minutes: filters.max_duration_minutes ?? null,
      max_changes: filters.max_changes ?? null,
      max_walking_meters: filters.max_walking_meters ?? null,
    }

    try {
      const res = await api.searchJourneys(payload)
      setResult(res)
    } catch (err) {
      setSearchError(err.message || 'Could not compute journeys right now. Please try again.')
    } finally {
      setSearching(false)
    }

    // Live context calls are independent -- one failing shouldn't block the others.
    api.weather(destination.latitude, destination.longitude).then(setWeather).catch(() => setWeather(null))
    api.cityPlaces(destination.latitude, destination.longitude, 6)
      .then((r) => setPlaces(r.places))
      .catch(() => setPlaces([]))
      .finally(() => setContextLoading(false))
    api.localFood(destination.latitude, destination.longitude, 9)
      .then((r) => setFood(r.food))
      .catch(() => setFood([]))
  }

  return (
    <div className="page">
      <Header />

      <section className="hero">
        <div className="hero-content">
          <h1>JOURNEYAI INDIA</h1>
          <p className="hero-sub">One search.<br />Every practical way there.</p>
          <p className="hero-desc">
            Compare cost, time, transfers, walking and emissions across India's transportation network.
          </p>

          <div className="search-box">
            <LocationSearch
              label="FROM"
              placeholder="Current location, city, station, landmark…"
              value={origin}
              onChange={setOrigin}
              allowCurrentLocation
            />
            <LocationSearch
              label="TO"
              placeholder="Where are you headed?"
              value={destination}
              onChange={setDestination}
              allowCurrentLocation={false}
            />

            <div className="search-box-row">
              <PrioritySelector value={priority} onChange={setPriority} />
            </div>

            <div className="search-box-row">
              <TransportFilters modes={modes} onChange={setModes} />
              <button type="button" className="filter-toggle" onClick={() => setShowFilters((v) => !v)}>
                {showFilters ? 'Hide filters' : 'More filters'}
              </button>
            </div>

            {showFilters && <FilterPanel filters={filters} onChange={setFilters} />}

            <button
              type="button"
              className="find-route-btn"
              onClick={handleSearch}
              disabled={!canSearch || searching}
            >
              {searching ? 'Finding routes…' : 'Find smartest route →'}
            </button>
            {searchError && <div className="search-error">{searchError}</div>}
          </div>
        </div>
      </section>

      {result && (
        <section className="results-section">
          <LiveContext
            origin={origin}
            destination={destination}
            weather={weather}
            roadDistanceKm={result.road_distance_km}
            transitAvailable={result.transit_available}
            loading={contextLoading && !weather}
          />

          {result.notes?.length > 0 && (
            <div className="result-notes">
              {result.notes.map((n, idx) => (
                <div key={idx} className="result-note">ℹ️ {n}</div>
              ))}
            </div>
          )}

          <JourneyMap
            origin={origin}
            destination={destination}
            segments={result.journeys[0]?.segments || []}
          />

          <h2 className="results-title">Recommended journeys</h2>
          {result.journeys.length === 0 ? (
            <div className="no-results">No journeys matched your filters. Try relaxing them above.</div>
          ) : (
            <div className="journey-list">
              {result.journeys.map((j) => (
                <JourneyCard key={j.id} journey={j} />
              ))}
            </div>
          )}

          <FamousPlaces places={places} cityName={destination?.name} loading={contextLoading && places === null} />
          <LocalFood spots={food} cityName={destination?.name} loading={contextLoading && food === null} />
        </section>
      )}

      <footer className="site-footer">
        <ApiStatus />
        <div className="footer-note">
          Map data © OpenStreetMap contributors · Places via Wikipedia · Weather via Open-Meteo
        </div>
      </footer>
    </div>
  )
}

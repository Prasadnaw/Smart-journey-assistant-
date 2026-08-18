import { useState } from 'react'
import { api } from '../api'

export default function CurrentLocationButton({ onLocated, label = '◎ Use current location' }) {
  const [status, setStatus] = useState('idle') // idle | locating | error
  const [error, setError] = useState('')

  const handleClick = () => {
    if (!('geolocation' in navigator)) {
      setStatus('error')
      setError('Your browser does not support location access.')
      return
    }
    setStatus('locating')
    setError('')

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords
        try {
          const place = await api.reverseGeocode(latitude, longitude)
          onLocated({
            name: place?.name || 'Current location',
            locality: place?.locality,
            state: place?.state,
            country: place?.country || 'India',
            latitude,
            longitude,
            raw_label: place?.raw_label || place?.name || `${latitude.toFixed(4)}, ${longitude.toFixed(4)}`,
          })
          setStatus('idle')
        } catch (e) {
          // Reverse geocoding failed, but we still have coordinates -- use them.
          onLocated({
            name: 'Current location',
            country: 'India',
            latitude,
            longitude,
            raw_label: `Current location (${latitude.toFixed(4)}, ${longitude.toFixed(4)})`,
          })
          setStatus('idle')
        }
      },
      (err) => {
        setStatus('error')
        if (err.code === err.PERMISSION_DENIED) {
          setError('Location access was denied. You can still type your location above.')
        } else if (err.code === err.POSITION_UNAVAILABLE) {
          setError('Your location could not be determined right now.')
        } else if (err.code === err.TIMEOUT) {
          setError('Location request timed out. Please try again.')
        } else {
          setError('Could not access your location.')
        }
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
    )
  }

  return (
    <div className="current-location">
      <button type="button" className="current-location-btn" onClick={handleClick} disabled={status === 'locating'}>
        {status === 'locating' ? 'Locating…' : label}
      </button>
      {status === 'error' && <div className="current-location-error">{error}</div>}
    </div>
  )
}

import { useEffect, useState } from 'react'
import { api } from '../api'

export default function ApiStatus() {
  const [status, setStatus] = useState(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    let mounted = true
    api.status()
      .then((s) => mounted && setStatus(s))
      .catch(() => mounted && setError(true))
    return () => { mounted = false }
  }, [])

  if (error) {
    return <div className="api-status api-status-error">Status check unavailable</div>
  }
  if (!status) return null

  const rows = [
    ['Geocoding', status.geocoding],
    ['Routing', status.routing],
    ['Weather', status.weather],
    ['Places', status.places],
    ['Transit', status.transit],
    ['Railway', status.railway],
  ]

  return (
    <div className="api-status">
      {rows.map(([label, value]) => (
        <div key={label} className="api-status-row">
          <span>{label}</span>
          <span className={value?.toLowerCase().includes('ok') || value?.toLowerCase().includes('connected') ? 'ok' : 'warn'}>
            {value}
          </span>
        </div>
      ))}
    </div>
  )
}

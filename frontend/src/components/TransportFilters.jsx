const MODES = [
  { id: 'train', label: '🚆 Train' },
  { id: 'metro', label: '🚇 Metro' },
  { id: 'bus', label: '🚌 Bus' },
  { id: 'walk', label: '🚶 Walk' },
  { id: 'taxi', label: '🚕 Taxi' },
]

const PRIORITIES = [
  { id: 'general', label: '▦ All options' },
  { id: 'fastest', label: '⚡ Fastest' },
  { id: 'cheapest', label: '💰 Cheapest' },
  { id: 'fewest_changes', label: '🔄 Fewest changes' },
  { id: 'least_walking', label: '🚶 Least walking' },
  { id: 'greenest', label: '🌱 Greenest' },
]

export function PrioritySelector({ value, onChange }) {
  return (
    <div className="priority-selector">
      {PRIORITIES.map((p) => (
        <button
          type="button"
          key={p.id}
          className={`priority-chip ${value === p.id ? 'active' : ''}`}
          onClick={() => onChange(p.id)}
        >
          {p.label}
        </button>
      ))}
    </div>
  )
}

export default function TransportFilters({ modes, onChange }) {
  const toggle = (id) => {
    if (modes.includes(id)) {
      onChange(modes.filter((m) => m !== id))
    } else {
      onChange([...modes, id])
    }
  }

  return (
    <div className="transport-filters">
      {MODES.map((m) => (
        <label
          key={m.id}
          className={`mode-checkbox ${
            modes.includes(m.id) ? 'active' : ''
          }`}
        >
          <input
            type="checkbox"
            checked={modes.includes(m.id)}
            onChange={() => toggle(m.id)}
          />
          {m.label}
        </label>
      ))}
    </div>
  )
}
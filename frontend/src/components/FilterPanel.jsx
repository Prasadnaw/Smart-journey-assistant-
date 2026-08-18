export default function FilterPanel({ filters, onChange }) {
  const update = (key, value) => {
    onChange({ ...filters, [key]: value === '' ? null : Number(value) })
  }

  return (
    <div className="filter-panel">
      <div className="filter-field">
        <label>Max fare (₹)</label>
        <input
          type="number"
          min="0"
          placeholder="Any"
          value={filters.max_fare_inr ?? ''}
          onChange={(e) => update('max_fare_inr', e.target.value)}
        />
      </div>
      <div className="filter-field">
        <label>Max journey time (min)</label>
        <input
          type="number"
          min="0"
          placeholder="Any"
          value={filters.max_duration_minutes ?? ''}
          onChange={(e) => update('max_duration_minutes', e.target.value)}
        />
      </div>
      <div className="filter-field">
        <label>Max transfers</label>
        <input
          type="number"
          min="0"
          placeholder="Any"
          value={filters.max_changes ?? ''}
          onChange={(e) => update('max_changes', e.target.value)}
        />
      </div>
      <div className="filter-field">
        <label>Max walking (m)</label>
        <input
          type="number"
          min="0"
          placeholder="Any"
          value={filters.max_walking_meters ?? ''}
          onChange={(e) => update('max_walking_meters', e.target.value)}
        />
      </div>
    </div>
  )
}

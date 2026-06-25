export function TodoFilter({ filter, onFilterChange, counts }) {
  const filters = [
    { key: 'all', label: `전체 (${counts.all})` },
    { key: 'active', label: `미완료 (${counts.active})` },
    { key: 'completed', label: `완료 (${counts.completed})` },
  ]

  return (
    <div className="todo-filter">
      {filters.map(f => (
        <button
          key={f.key}
          className={`filter-btn${filter === f.key ? ' active' : ''}`}
          onClick={() => onFilterChange(f.key)}
        >
          {f.label}
        </button>
      ))}
    </div>
  )
}

/**
 * Card de filtro por categoría para DocumentsPage.
 * @param {{ cat: { category_id, category_name, color, count }, active, onClick }} props
 */
export default function CategoryFilterCard({ cat, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className="flex flex-col items-start gap-1 px-3 py-2.5 rounded-[var(--radius-md)] border transition-all duration-150 shrink-0 min-w-[110px]"
      style={{
        backgroundColor: active ? 'var(--color-primary-subtle)' : 'var(--color-bg-surface)',
        borderColor: active ? 'var(--color-primary)' : 'var(--color-border)',
        boxShadow: active ? '0 0 0 1px var(--color-primary)' : 'none',
      }}
    >
      <div className="flex items-center gap-1.5">
        <span
          className="w-2 h-2 rounded-full shrink-0"
          style={{ backgroundColor: cat.color ?? 'var(--color-primary)' }}
        />
        <span
          className="text-xs font-medium truncate max-w-[80px]"
          style={{ color: active ? 'var(--color-primary)' : 'var(--color-text-secondary)' }}
        >
          {cat.category_name}
        </span>
      </div>
      <span
        className="text-lg font-semibold leading-none"
        style={{ color: active ? 'var(--color-primary)' : 'var(--color-text-primary)' }}
      >
        {cat.count}
      </span>
    </button>
  )
}

/**
 * @param {{ label: string, value: string|number, icon?: React.ReactNode,
 *           trend?: string, iconBg?: string, iconColor?: string }} props
 */
export default function StatCard({ label, value, icon, trend, iconBg, iconColor }) {
  return (
    <div
      className="card-hover glow-primary-hover flex items-start justify-between rounded-[var(--radius-xl)] p-5 anim-fade-in-up"
      style={{
        backgroundColor: 'var(--color-bg-surface)',
        border: '1px solid var(--color-border)',
      }}
    >
      <div className="min-w-0">
        <p
          className="text-xs font-medium uppercase tracking-wide mb-2"
          style={{ color: 'var(--color-text-muted)' }}
        >
          {label}
        </p>
        <p
          className="text-3xl font-bold leading-none tabular-nums"
          style={{ color: 'var(--color-text-primary)' }}
        >
          {value ?? '—'}
        </p>
        {trend && (
          <p className="text-xs mt-2" style={{ color: 'var(--color-text-muted)' }}>
            {trend}
          </p>
        )}
      </div>

      {icon && (
        <div
          className="w-9 h-9 rounded-[var(--radius-md)] flex items-center justify-center shrink-0 transition-transform duration-200 group-hover:scale-110"
          style={{
            backgroundColor: iconBg ?? 'var(--color-primary-subtle)',
            color: iconColor ?? 'var(--color-primary)',
          }}
        >
          {icon}
        </div>
      )}
    </div>
  )
}

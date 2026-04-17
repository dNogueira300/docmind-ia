import clsx from 'clsx'

/**
 * @param {{ label?: string, error?: string, className?, id?, type?, ...rest }} props
 */
export default function Input({ label, error, className, id, ...props }) {
  const inputId = id ?? label?.toLowerCase().replace(/\s+/g, '-')

  return (
    <div className={clsx('flex flex-col gap-1', className)}>
      {label && (
        <label
          htmlFor={inputId}
          className="text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wide"
        >
          {label}
        </label>
      )}
      <input
        id={inputId}
        className={clsx(
          'w-full px-3 py-2 text-sm rounded-[var(--radius-md)] border bg-[var(--color-bg-surface-2)]',
          'text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)]',
          'transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:ring-offset-0',
          error
            ? 'border-[var(--color-error)] focus:ring-[var(--color-error)]'
            : 'border-[var(--color-border)] focus:border-[var(--color-primary)]'
        )}
        {...props}
      />
      {error && (
        <p className="text-xs text-[var(--color-error)]">{error}</p>
      )}
    </div>
  )
}

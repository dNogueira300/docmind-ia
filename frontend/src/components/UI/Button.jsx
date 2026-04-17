import clsx from 'clsx'

/**
 * @param {{ variant?: 'primary'|'secondary'|'ghost'|'danger',
 *           size?: 'sm'|'md'|'lg', loading?: boolean,
 *           disabled?: boolean, children, className?, onClick?, type? }} props
 */
export default function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  children,
  className,
  ...props
}) {
  const base = [
    'inline-flex items-center justify-center gap-2 font-medium',
    'rounded-[var(--radius-md)]',
    'transition-all duration-150 ease-out',
    'focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)] focus-visible:ring-offset-1',
    'cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed',
    'active:scale-[0.97]',   /* feedback táctil en press */
  ].join(' ')

  const variants = {
    primary: clsx(
      'bg-[var(--color-primary)] text-white',
      'hover:bg-[var(--color-primary-hover)] hover:-translate-y-px hover:shadow-md',
      'active:bg-[var(--color-primary-active)]',
    ),
    secondary: clsx(
      'border border-[var(--color-primary)] text-[var(--color-primary)] bg-transparent',
      'hover:bg-[var(--color-primary-subtle)] hover:-translate-y-px',
    ),
    ghost: clsx(
      'border border-[var(--color-border)] text-[var(--color-text-secondary)] bg-transparent',
      'hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)]',
      'hover:border-[var(--color-text-muted)]',
    ),
    danger: clsx(
      'bg-[var(--color-error)] text-white',
      'hover:opacity-90 hover:-translate-y-px',
    ),
  }

  const sizes = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2 text-sm',
    lg: 'px-5 py-2.5 text-sm',
  }

  return (
    <button
      disabled={disabled || loading}
      className={clsx(base, variants[variant], sizes[size], className)}
      {...props}
    >
      {loading && (
        <svg className="animate-spin h-3.5 w-3.5 shrink-0" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
        </svg>
      )}
      {children}
    </button>
  )
}

import { FileSearch } from 'lucide-react'

/** @param {{ title: string, description?: string, action?: React.ReactNode, icon?: React.ReactNode }} props */
export default function EmptyState({ title, description, action, icon }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      <div className="w-12 h-12 rounded-[var(--radius-lg)] bg-[var(--color-bg-surface-2)] flex items-center justify-center mb-4 text-[var(--color-text-muted)]">
        {icon ?? <FileSearch size={22} />}
      </div>
      <p className="text-sm font-medium text-[var(--color-text-primary)] mb-1">{title}</p>
      {description && (
        <p className="text-xs text-[var(--color-text-muted)] max-w-xs mb-4">{description}</p>
      )}
      {action}
    </div>
  )
}

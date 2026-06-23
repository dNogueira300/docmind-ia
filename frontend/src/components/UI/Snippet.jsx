/**
 * Renderiza un fragmento de texto de búsqueda resaltando los términos que
 * coinciden. El backend (ts_headline) marca las coincidencias entre « y ».
 */
export default function Snippet({ text, className = '' }) {
  if (!text) return null
  const parts = text.split(/(«[^»]*»)/g)
  return (
    <p className={className}>
      {parts.map((part, i) =>
        part.startsWith('«') && part.endsWith('»') ? (
          <mark
            key={i}
            style={{
              backgroundColor: 'var(--color-primary-subtle)',
              color: 'var(--color-primary)',
              padding: '0 2px',
              borderRadius: '2px',
            }}
          >
            {part.slice(1, -1)}
          </mark>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </p>
  )
}

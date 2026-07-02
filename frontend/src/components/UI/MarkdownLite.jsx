/**
 * Renderizador de markdown ligero para las respuestas del asistente IA.
 *
 * Soporta un subconjunto seguro (sin dangerouslySetInnerHTML): **negrita**,
 * *cursiva*, `código`, viñetas ("- ", "* ", "• "), listas numeradas y saltos de
 * línea. Suficiente para el formato que devuelve Gemini, sin añadir dependencias.
 */

// Divide una línea en nodos aplicando negrita/cursiva/código en línea.
function parseInline(text, keyBase) {
  const nodes = []
  const re = /\*\*(.+?)\*\*|__(.+?)__|\*(.+?)\*|`(.+?)`/g
  let last = 0
  let m
  let i = 0
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) nodes.push(text.slice(last, m.index))
    if (m[1] !== undefined) nodes.push(<strong key={`${keyBase}-b${i}`}>{m[1]}</strong>)
    else if (m[2] !== undefined) nodes.push(<strong key={`${keyBase}-b${i}`}>{m[2]}</strong>)
    else if (m[3] !== undefined) nodes.push(<em key={`${keyBase}-i${i}`}>{m[3]}</em>)
    else if (m[4] !== undefined) {
      nodes.push(
        <code key={`${keyBase}-c${i}`} className="px-1 py-0.5 rounded bg-black/5 text-[0.9em]">
          {m[4]}
        </code>
      )
    }
    last = re.lastIndex
    i++
  }
  if (last < text.length) nodes.push(text.slice(last))
  return nodes
}

export default function MarkdownLite({ text }) {
  const raw = (text || '').toString()
  const lines = raw.split('\n')

  const out = []
  let bullets = null   // acumulador de <li> para una lista contigua

  const flushBullets = () => {
    if (bullets && bullets.length) {
      out.push(
        <ul key={`ul-${out.length}`} className="list-disc pl-5 my-1 space-y-0.5">
          {bullets}
        </ul>
      )
    }
    bullets = null
  }

  lines.forEach((line, idx) => {
    const bullet = line.match(/^\s*[-*•]\s+(.*)/)
    const numbered = line.match(/^\s*\d+[.)]\s+(.*)/)

    if (bullet || numbered) {
      const content = (bullet ? bullet[1] : numbered[1])
      if (!bullets) bullets = []
      bullets.push(<li key={`li-${idx}`}>{parseInline(content, `li-${idx}`)}</li>)
      return
    }

    flushBullets()

    if (line.trim() === '') {
      out.push(<div key={`sp-${idx}`} className="h-2" />)
      return
    }

    out.push(<p key={`p-${idx}`} className="my-0.5">{parseInline(line, `p-${idx}`)}</p>)
  })

  flushBullets()

  return <>{out}</>
}

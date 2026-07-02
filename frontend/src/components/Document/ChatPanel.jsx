import { useState, useRef, useEffect } from 'react'
import { Send, BrainCircuit, User, Loader2, MessageSquare, ChevronDown, ChevronUp } from 'lucide-react'
import { chatWithDocument } from '../../services/api/chat'
import MarkdownLite from '../UI/MarkdownLite'

function Message({ role, content }) {
  const isUser = role === 'user'
  return (
    <div className={`flex gap-2 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar */}
      <div
        className="w-6 h-6 rounded-full flex items-center justify-center shrink-0 mt-0.5"
        style={{
          backgroundColor: isUser ? 'var(--color-primary)' : 'var(--color-ai-subtle)',
          border: isUser ? 'none' : '1px solid var(--color-primary-border)',
        }}
      >
        {isUser
          ? <User size={11} className="text-white" />
          : <BrainCircuit size={11} style={{ color: 'var(--color-ai-accent)' }} />
        }
      </div>

      {/* Burbuja */}
      <div
        className="max-w-[85%] px-3 py-2 rounded-[var(--radius-md)] text-xs leading-relaxed"
        style={{
          backgroundColor: isUser ? 'var(--color-primary)' : 'var(--color-bg-surface-2)',
          color: isUser ? '#fff' : 'var(--color-text-primary)',
          border: isUser ? 'none' : '1px solid var(--color-border)',
        }}
      >
        {isUser ? content : <MarkdownLite text={content} />}
      </div>
    </div>
  )
}

/**
 * @param {{ documentId: string, docName: string, initiallyOpen?: boolean,
 *          history?: Array, onHistoryChange?: Function }} props
 *
 * Si se pasan `history` y `onHistoryChange`, el estado de la conversación es
 * controlado por el componente padre (para que sobreviva al desmontar/montar,
 * p.ej. al cambiar de pestaña). Si no, usa estado interno.
 */
export default function ChatPanel({
  documentId, docName, initiallyOpen = false,
  history: controlledHistory, onHistoryChange,
}) {
  const [open, setOpen]                 = useState(initiallyOpen)
  const [localHistory, setLocalHistory] = useState([])
  const history    = controlledHistory ?? localHistory
  const setHistory = onHistoryChange ?? setLocalHistory
  const [input, setInput]     = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef             = useRef(null)
  const inputRef              = useRef(null)

  // Auto-scroll al último mensaje
  useEffect(() => {
    if (open) bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [history, open])

  // Foco en el input al abrir
  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 100)
  }, [open])

  const handleSend = async (text) => {
    const msg = (text ?? input).trim()
    if (!msg || loading) return

    setInput('')
    setLoading(true)

    // Agregar mensaje del usuario de forma optimista
    const optimisticHistory = [
      ...history,
      { role: 'user', content: msg },
    ]
    setHistory(optimisticHistory)

    try {
      const { history: newHistory } = await chatWithDocument(documentId, msg, history)
      setHistory(newHistory)
    } catch {
      setHistory([
        ...optimisticHistory,
        { role: 'assistant', content: 'Error al conectar con el asistente. Intenta de nuevo.' },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div
      className="rounded-[var(--radius-md)] overflow-hidden border"
      style={{ borderColor: 'var(--color-primary-border)' }}
    >
      {/* Header — clic abre/cierra */}
      <button
        className="w-full flex items-center justify-between px-3 py-2.5 transition-colors"
        style={{
          backgroundColor: open ? 'var(--color-primary-subtle)' : 'var(--color-bg-surface-2)',
        }}
        onClick={() => setOpen((v) => !v)}
      >
        <div className="flex items-center gap-2">
          <BrainCircuit size={14} style={{ color: 'var(--color-ai-accent)' }} />
          <span className="text-xs font-semibold" style={{ color: 'var(--color-ai-accent)' }}>
            Consultar a DocMind
          </span>
          {history.length > 0 && (
            <span
              className="text-[10px] px-1.5 py-0.5 rounded-full font-medium"
              style={{ backgroundColor: 'var(--color-ai-subtle)', color: 'var(--color-ai-accent)' }}
            >
              {Math.floor(history.length / 2)} pregunta{history.length > 2 ? 's' : ''}
            </span>
          )}
        </div>
        {open
          ? <ChevronUp size={13} style={{ color: 'var(--color-text-muted)' }} />
          : <ChevronDown size={13} style={{ color: 'var(--color-text-muted)' }} />
        }
      </button>

      {/* Panel expandido */}
      {open && (
        <div className="flex flex-col" style={{ backgroundColor: 'var(--color-bg-surface)' }}>
          {/* Lista de mensajes */}
          <div
            className="flex flex-col gap-3 p-3 overflow-y-auto"
            style={{ maxHeight: '260px', minHeight: '80px' }}
          >
            {history.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-4 gap-2 opacity-60">
                <BrainCircuit size={22} style={{ color: 'var(--color-text-muted)' }} />
                <p className="text-xs text-center" style={{ color: 'var(--color-text-muted)' }}>
                  Pregúntale a DocMind sobre este documento
                </p>
                <div className="flex flex-wrap gap-1.5 justify-center mt-1">
                  {['¿De qué trata?', '¿Quiénes son las partes?', '¿Cuándo vence?'].map((s) => (
                    <button
                      key={s}
                      onClick={() => handleSend(s)}
                      className="text-[10px] px-2 py-1 rounded-full border transition-colors"
                      style={{
                        borderColor: 'var(--color-primary-border)',
                        color: 'var(--color-primary)',
                        backgroundColor: 'var(--color-primary-subtle)',
                      }}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              history.map((msg, i) => (
                <Message key={i} role={msg.role} content={msg.content} />
              ))
            )}
            {loading && (
              <div className="flex gap-2">
                <div
                  className="w-6 h-6 rounded-full flex items-center justify-center shrink-0"
                  style={{ backgroundColor: 'var(--color-ai-subtle)', border: '1px solid var(--color-primary-border)' }}
                >
                  <BrainCircuit size={11} style={{ color: 'var(--color-ai-accent)' }} />
                </div>
                <div
                  className="flex items-center gap-1.5 px-3 py-2 rounded-[var(--radius-md)] text-xs"
                  style={{ backgroundColor: 'var(--color-bg-surface-2)', border: '1px solid var(--color-border)' }}
                >
                  <Loader2 size={11} className="animate-spin" style={{ color: 'var(--color-ai-accent)' }} />
                  <span style={{ color: 'var(--color-text-muted)' }}>Pensando…</span>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div
            className="flex items-end gap-2 p-2 border-t"
            style={{ borderColor: 'var(--color-border)' }}
          >
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Escribe tu pregunta… (Enter para enviar)"
              rows={1}
              disabled={loading}
              className="flex-1 px-3 py-2 text-xs rounded-[var(--radius-md)] resize-none focus:outline-none focus:ring-1 focus:ring-[var(--color-primary)] disabled:opacity-50"
              style={{
                backgroundColor: 'var(--color-bg-surface-2)',
                border: '1px solid var(--color-border)',
                color: 'var(--color-text-primary)',
                maxHeight: '80px',
              }}
            />
            <button
              onClick={() => handleSend()}
              disabled={!input.trim() || loading}
              className="p-2 rounded-[var(--radius-md)] transition-colors disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
              style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}
              onMouseEnter={(e) => { if (!loading && input.trim()) e.currentTarget.style.backgroundColor = 'var(--color-primary-hover)' }}
              onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'var(--color-primary)' }}
            >
              <Send size={13} />
            </button>
          </div>

          {/* Footer — powered by */}
          <p
            className="text-center text-[9px] pb-1.5"
            style={{ color: 'var(--color-text-muted)' }}
          >
            DocMind IA · respuestas basadas en el contenido del documento
          </p>
        </div>
      )}
    </div>
  )
}

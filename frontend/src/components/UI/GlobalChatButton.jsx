import { useState, useRef, useEffect } from 'react'
import { BrainCircuit, X, Send, Loader2, RotateCcw } from 'lucide-react'
import { chatGlobal } from '../../services/api/chat'
import { useAuth } from '../../context/AuthContext'

const SUGGESTIONS = [
  '¿Cuántos documentos hay en el sistema?',
  '¿Quién ha subido más archivos?',
  '¿Cuál fue el último documento subido?',
  '¿Hay alertas de vencimiento pendientes?',
  '¿Qué categorías existen?',
]

function Message({ role, content }) {
  const isUser = role === 'user'
  return (
    <div className={`flex gap-2.5 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar */}
      <div
        className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5"
        style={{
          background: isUser
            ? 'var(--color-primary)'
            : 'linear-gradient(135deg, var(--color-ai-accent), var(--color-primary))',
        }}
      >
        {isUser
          ? <span className="text-white text-[10px] font-bold">Tú</span>
          : <BrainCircuit size={13} className="text-white" />
        }
      </div>

      {/* Burbuja */}
      <div
        className="max-w-[82%] px-3 py-2.5 rounded-[var(--radius-lg)] text-xs leading-relaxed"
        style={{
          backgroundColor: isUser ? 'var(--color-primary)' : 'var(--color-bg-surface-2)',
          color: isUser ? '#fff' : 'var(--color-text-primary)',
          border: isUser ? 'none' : '1px solid var(--color-border)',
        }}
      >
        {content}
      </div>
    </div>
  )
}

export default function GlobalChatButton() {
  const { isAuthenticated } = useAuth()
  const [open,    setOpen]    = useState(false)
  const [history, setHistory] = useState([])
  const [input,   setInput]   = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)
  const inputRef  = useRef(null)

  // No mostrar si no está autenticado
  if (!isAuthenticated) return null

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [history, loading])

  // Focus al abrir
  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 150)
  }, [open])

  const sendMessage = async (msg) => {
    const text = msg.trim()
    if (!text || loading) return
    setInput('')
    setLoading(true)

    const optimistic = [...history, { role: 'user', content: text }]
    setHistory(optimistic)

    try {
      const { history: newHistory } = await chatGlobal(text, history)
      setHistory(newHistory)
    } catch {
      setHistory([...optimistic, { role: 'assistant', content: 'Error al conectar. Intenta de nuevo.' }])
    } finally {
      setLoading(false)
    }
  }

  const handleSend = () => sendMessage(input)

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
  }

  return (
    <>
      {/* ── Panel de chat ── */}
      {open && (
        <div
          className="fixed z-40 flex flex-col shadow-2xl rounded-[var(--radius-xl)] overflow-hidden"
          style={{
            bottom: '84px',
            right: '24px',
            width: '380px',
            height: '520px',
            backgroundColor: 'var(--color-bg-surface)',
            border: '1px solid var(--color-border)',
          }}
        >
          {/* Header */}
          <div
            className="flex items-center gap-3 px-4 py-3 shrink-0"
            style={{
              background: 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-ai-accent) 100%)',
            }}
          >
            <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center">
              <BrainCircuit size={16} className="text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-white leading-none">DocMind</p>
              <p className="text-[10px] text-white/70 mt-0.5">Asistente inteligente del sistema</p>
            </div>
            <div className="flex items-center gap-1">
              {history.length > 0 && (
                <button
                  onClick={() => setHistory([])}
                  className="p-1.5 rounded-full text-white/70 hover:text-white hover:bg-white/20 transition-colors"
                  title="Nueva conversación"
                >
                  <RotateCcw size={13} />
                </button>
              )}
              <button
                onClick={() => setOpen(false)}
                className="p-1.5 rounded-full text-white/70 hover:text-white hover:bg-white/20 transition-colors"
              >
                <X size={15} />
              </button>
            </div>
          </div>

          {/* Mensajes */}
          <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
            {history.length === 0 ? (
              <div className="flex flex-col gap-3 pt-2">
                <div className="text-center">
                  <div
                    className="w-12 h-12 rounded-full mx-auto mb-3 flex items-center justify-center"
                    style={{ background: 'linear-gradient(135deg, var(--color-primary-subtle), var(--color-ai-subtle))' }}
                  >
                    <BrainCircuit size={22} style={{ color: 'var(--color-ai-accent)' }} />
                  </div>
                  <p className="text-sm font-medium" style={{ color: 'var(--color-text-primary)' }}>
                    Hola, soy DocMind
                  </p>
                  <p className="text-xs mt-1" style={{ color: 'var(--color-text-muted)' }}>
                    Puedo ayudarte con estadísticas, documentos y cualquier consulta sobre el sistema.
                  </p>
                </div>

                <div className="flex flex-col gap-1.5 mt-2">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => sendMessage(s)}
                      className="text-left text-xs px-3 py-2 rounded-[var(--radius-md)] transition-colors border"
                      style={{
                        borderColor: 'var(--color-border)',
                        backgroundColor: 'var(--color-bg-surface-2)',
                        color: 'var(--color-text-secondary)',
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.borderColor = 'var(--color-primary)'
                        e.currentTarget.style.color = 'var(--color-primary)'
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.borderColor = 'var(--color-border)'
                        e.currentTarget.style.color = 'var(--color-text-secondary)'
                      }}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              history.map((msg, i) => <Message key={i} role={msg.role} content={msg.content} />)
            )}

            {loading && (
              <div className="flex gap-2.5">
                <div
                  className="w-7 h-7 rounded-full flex items-center justify-center shrink-0"
                  style={{ background: 'linear-gradient(135deg, var(--color-ai-accent), var(--color-primary))' }}
                >
                  <BrainCircuit size={13} className="text-white" />
                </div>
                <div
                  className="flex items-center gap-2 px-3 py-2.5 rounded-[var(--radius-lg)] text-xs"
                  style={{ backgroundColor: 'var(--color-bg-surface-2)', border: '1px solid var(--color-border)' }}
                >
                  <Loader2 size={12} className="animate-spin" style={{ color: 'var(--color-ai-accent)' }} />
                  <span style={{ color: 'var(--color-text-muted)' }}>DocMind está pensando…</span>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div
            className="flex items-end gap-2 p-3 border-t shrink-0"
            style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-bg-surface)' }}
          >
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Escribe tu pregunta… (Enter para enviar)"
              rows={1}
              disabled={loading}
              className="flex-1 px-3 py-2 text-xs rounded-[var(--radius-md)] resize-none focus:outline-none disabled:opacity-50"
              style={{
                backgroundColor: 'var(--color-bg-surface-2)',
                border: '1px solid var(--color-border)',
                color: 'var(--color-text-primary)',
                maxHeight: '80px',
              }}
              onFocus={(e) => (e.currentTarget.style.borderColor = 'var(--color-primary)')}
              onBlur={(e) => (e.currentTarget.style.borderColor = 'var(--color-border)')}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || loading}
              className="p-2.5 rounded-[var(--radius-md)] transition-all disabled:opacity-40 disabled:cursor-not-allowed"
              style={{ background: 'linear-gradient(135deg, var(--color-primary), var(--color-ai-accent))', color: '#fff' }}
            >
              <Send size={14} />
            </button>
          </div>
        </div>
      )}

      {/* ── Botón flotante ── */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="fixed z-40 w-14 h-14 rounded-full shadow-lg flex items-center justify-center transition-all duration-200 hover:scale-110 active:scale-95"
        style={{
          bottom: '24px',
          right: '24px',
          background: open
            ? 'var(--color-bg-surface-2)'
            : 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-ai-accent) 100%)',
          border: open ? '2px solid var(--color-border)' : 'none',
          boxShadow: '0 8px 32px rgba(45,127,249,0.35)',
        }}
        title={open ? 'Cerrar DocMind' : 'Abrir DocMind IA'}
      >
        {open
          ? <X size={20} style={{ color: 'var(--color-text-secondary)' }} />
          : <BrainCircuit size={22} className="text-white" />
        }
      </button>
    </>
  )
}

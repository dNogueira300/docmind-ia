import { createContext, useContext, useState, useCallback, useRef } from 'react'
import Toast from '../components/UI/Toast'

const ToastContext = createContext(null)

let _idCounter = 0

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const timersRef = useRef({})

  const dismiss = useCallback((id) => {
    clearTimeout(timersRef.current[id])
    delete timersRef.current[id]
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const show = useCallback((type, title, message) => {
    const id = ++_idCounter
    const duration = type === 'error' || type === 'warning' ? 6000 : 4000

    setToasts((prev) => {
      // Máximo 3 toasts visibles
      const trimmed = prev.length >= 3 ? prev.slice(1) : prev
      return [...trimmed, { id, type, title, message, duration }]
    })

    timersRef.current[id] = setTimeout(() => dismiss(id), duration)
    return id
  }, [dismiss])

  const toast = {
    success: (title, message) => show('success', title, message),
    error:   (title, message) => show('error',   title, message),
    warning: (title, message) => show('warning', title, message),
    info:    (title, message) => show('info',    title, message),
  }

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <Toast toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast debe usarse dentro de ToastProvider')
  return ctx
}

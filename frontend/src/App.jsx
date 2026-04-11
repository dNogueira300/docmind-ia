import { BrowserRouter, Routes, Route } from 'react-router-dom'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<div className="min-h-screen bg-slate-50 flex items-center justify-center">
          <h1 className="text-2xl font-semibold text-slate-800">DocMind IA</h1>
        </div>} />
      </Routes>
    </BrowserRouter>
  )
}

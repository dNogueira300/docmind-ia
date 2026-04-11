from fastapi import FastAPI

app = FastAPI(
    title="DocMind IA",
    description="Sistema de Gestión Documental Inteligente con IA",
    version="0.1.0",
)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "DocMind IA Backend"}
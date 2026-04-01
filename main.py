from pathlib import Path
import asyncio
import json
import io
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from excel import procesar_excel, procesar_excel_progreso

app = FastAPI()

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = STATIC_DIR / "index.html"
    return html_path.read_text(encoding="utf-8")


@app.post("/procesar")
async def procesar(file: UploadFile = File(...)):
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos .xlsx")

    file_bytes = await file.read()
    filename_out = file.filename.replace(".xlsx", "_completado.xlsx")

    async def generate():
        loop = asyncio.get_event_loop()
        gen = procesar_excel_progreso(file_bytes)
        _done = object()

        yield f"data: {json.dumps({'tipo': 'inicio', 'nombre': filename_out})}\n\n"

        try:
            while True:
                evento = await loop.run_in_executor(None, next, gen, _done)
                if evento is _done:
                    break
                if evento["tipo"] == "listo":
                    evento["nombre"] = filename_out
                yield f"data: {json.dumps(evento)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'tipo': 'error', 'mensaje': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

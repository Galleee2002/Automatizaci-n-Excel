from pathlib import Path
import asyncio
import json
import logging
import time
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from excel import procesar_excel_progreso

logger = logging.getLogger(__name__)

app = FastAPI()

STATIC_DIR = Path(__file__).parent / "static"


_NO_CACHE_HTML = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
}


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = STATIC_DIR / "index.html"
    return HTMLResponse(
        content=html_path.read_text(encoding="utf-8"),
        headers=_NO_CACHE_HTML,
    )


@app.post("/procesar")
async def procesar(file: UploadFile = File(...)):
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos .xlsx")

    t_req0 = time.perf_counter()
    t_read0 = time.perf_counter()
    file_bytes = await file.read()
    lectura_upload_s = time.perf_counter() - t_read0
    logger.info(
        "lectura upload: %.3f s | %d bytes",
        lectura_upload_s,
        len(file_bytes),
    )
    filename_out = file.filename.replace(".xlsx", "_completado.xlsx")

    async def generate():
        loop = asyncio.get_event_loop()
        gen = procesar_excel_progreso(file_bytes)
        _done = object()

        def sse(payload: dict) -> str:
            body = {**payload, "elapsed_s": round(time.perf_counter() - t_req0, 3)}
            return f"data: {json.dumps(body)}\n\n"

        yield sse(
            {
                "tipo": "inicio",
                "nombre": filename_out,
                "lectura_upload_s": lectura_upload_s,
            }
        )

        try:
            while True:
                evento = await loop.run_in_executor(None, next, gen, _done)
                if evento is _done:
                    break
                out = dict(evento)
                if out["tipo"] == "listo":
                    out["nombre"] = filename_out
                yield sse(out)
        except Exception as e:
            yield sse({"tipo": "error", "mensaje": str(e)})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

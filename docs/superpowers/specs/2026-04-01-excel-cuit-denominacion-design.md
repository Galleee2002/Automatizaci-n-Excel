# Design: Excel CUIT → Denominacion Auto-fill

**Date:** 2026-04-01
**Status:** Approved

## Context

Se necesita un sistema web que permita subir un archivo Excel con CUITs en la columna A ("Donante/Donatario") y que complete automáticamente la columna B ("Denominacion") consultando cuitonline.com. El Excel puede tener más columnas; solo se modifica la columna B, el resto se preserva intacto.

## Architecture

```
[Browser]
   │  Upload .xlsx
   ▼
[FastAPI Backend]
   │  Read column A (CUITs)
   │  For each CUIT → fetch cuitonline.com → extract denomination
   │  Write denomination to column B only
   ▼
[Browser]
   Download completed .xlsx (all columns intact)
```

## Components

### `main.py` — FastAPI server
- Single endpoint: `POST /procesar`
- Accepts multipart file upload
- Calls `excel.py` and `scraper.py`
- Returns the processed file as a downloadable response

### `scraper.py` — cuitonline.com lookup
- Function: `get_denominacion(cuit: str) -> str`
- Uses `httpx` (async) to fetch the page for a given CUIT
- Uses `BeautifulSoup4` to parse and extract the denomination
- Retry once on network error; if still fails → returns empty string
- 0.5s delay between requests to avoid being blocked

### `excel.py` — Excel processing
- Function: `procesar_excel(file_bytes) -> bytes`
- Opens the workbook with `openpyxl` (preserves all existing data and styles)
- Iterates rows starting from row 2 (skips header)
- Reads CUIT from column A, calls `get_denominacion(cuit)`
- Writes result to column B only
- If CUIT not found → writes "NO ENCONTRADO"
- Returns the modified workbook as bytes

### `index.html` — Frontend UI
- File input for `.xlsx` selection
- "Procesar" button that POSTs the file to `/procesar`
- Status indicator: "Procesando..." → "Listo"
- Auto-triggers download of the returned file

## Tech Stack

| Component | Library |
|-----------|---------|
| Web server | FastAPI + uvicorn |
| Excel read/write | openpyxl |
| HTTP requests | httpx (async) |
| HTML parsing | BeautifulSoup4 |
| Frontend | Vanilla HTML/JS |

## Excel Structure (real file)

- Fila 1–12: metadatos y encabezados decorativos (no tocar)
- Fila 13: encabezados reales (`CUIT\nDonante/\nDonatario`, `Denominación`, ...)
- Fila 14: vacía (no tocar)
- Fila 15+: datos. CUIT almacenado como entero (ej. `27172867923`)
- Se procesan solo filas 15 en adelante

## Lógica de escritura

- **Solo se completan celdas vacías** en columna B — si ya tiene valor, se respeta
- El CUIT (entero) debe convertirse a string para la consulta a cuitonline.com

## Error Handling

| Scenario | Behavior |
|----------|----------|
| CUIT no encontrado en cuitonline.com | Escribe "NO ENCONTRADO" en columna B |
| Error de red | Reintenta 1 vez; si falla, deja celda vacía |
| Columna A vacía en una fila | Salta esa fila sin modificar |
| Columna B ya tiene valor | No modifica esa celda |

## File Structure

```
Automatización-Excel/
├── main.py
├── scraper.py
├── excel.py
├── requirements.txt
└── static/
    └── index.html
```

## Verification

1. `pip install -r requirements.txt`
2. `uvicorn main:app --reload`
3. Abrir `http://localhost:8000` en el navegador
4. Subir un `.xlsx` con CUITs en columna A
5. Verificar que columna B se completa con denominaciones
6. Verificar que todas las demás columnas permanecen intactas
7. Verificar que CUITs inválidos muestran "NO ENCONTRADO"

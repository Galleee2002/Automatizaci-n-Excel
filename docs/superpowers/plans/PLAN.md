# Excel CUIT → Denominacion Auto-fill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Web app donde el usuario sube un `.xlsx`, el sistema completa la columna B ("Denominación") consultando cuitonline.com para cada CUIT en columna A, y devuelve el archivo para descargar.

**Architecture:** FastAPI sirve un endpoint `POST /procesar` y el HTML estático. El módulo `scraper.py` hace GET a `https://www.cuitonline.com/search.php?q={cuit}` y extrae el texto de `a.denominacion`. El módulo `excel.py` abre el workbook, itera desde fila 15, solo escribe en columna B si está vacía, y devuelve los bytes del archivo modificado.

**Tech Stack:** Python 3.x, FastAPI, uvicorn, openpyxl, requests, beautifulsoup4, python-multipart, pytest

---

## File Map

| Archivo | Rol |
|---------|-----|
| `requirements.txt` | Dependencias del proyecto |
| `scraper.py` | `get_denominacion(cuit: str) -> str` — consulta cuitonline.com |
| `excel.py` | `procesar_excel(file_bytes: bytes) -> bytes` — lee/escribe workbook |
| `main.py` | FastAPI app: `POST /procesar`, sirve `static/index.html` |
| `static/index.html` | UI: file input + botón procesar + descarga automática |
| `tests/test_scraper.py` | Tests unitarios del scraper (HTTP mockeado) |
| `tests/test_excel.py` | Tests unitarios del procesador de Excel |

---

## Task 1: Setup del proyecto

**Files:**
- Create: `requirements.txt`
- Create: `tests/__init__.py`

- [ ] **Step 1: Crear `requirements.txt`**

```
fastapi==0.115.0
uvicorn==0.30.6
openpyxl==3.1.5
requests==2.32.3
beautifulsoup4==4.12.3
python-multipart==0.0.9
pytest==8.3.3
```

- [ ] **Step 2: Instalar dependencias**

```bash
pip install -r requirements.txt
```

Salida esperada: `Successfully installed fastapi uvicorn openpyxl requests beautifulsoup4 python-multipart pytest` (puede variar si ya están instalados)

- [ ] **Step 3: Crear directorio de tests y `__init__.py` vacío**

```bash
mkdir -p tests static
touch tests/__init__.py
```

- [ ] **Step 4: Commit**

```bash
git init
git add requirements.txt tests/__init__.py
git commit -m "chore: project setup with dependencies"
```

---

## Task 2: Scraper de cuitonline.com

**Files:**
- Create: `scraper.py`
- Create: `tests/test_scraper.py`

### URL y selector validados
- URL: `https://www.cuitonline.com/search.php?q={cuit}`
- El nombre aparece en: `<a class="denominacion">NOMBRE</a>`
- Cuando no hay resultados: no existe elemento `a.denominacion`

- [ ] **Step 1: Escribir tests que fallan**

Crear `tests/test_scraper.py`:

```python
from unittest.mock import patch, MagicMock
from scraper import get_denominacion


def _make_response(html: str, status: int = 200):
    mock = MagicMock()
    mock.status_code = status
    mock.text = html
    mock.raise_for_status = MagicMock()
    return mock


FOUND_HTML = """
<html><body>
  <div class="hit">
    <a class="denominacion" href="/detalle/30712505873/cigars.html">CIGARS SONS S.R.L.</a>
  </div>
</body></html>
"""

NOT_FOUND_HTML = """
<html><body>
  <div class="results">No se encontraron resultados.</div>
</body></html>
"""


def test_get_denominacion_found():
    with patch("scraper.requests.get", return_value=_make_response(FOUND_HTML)):
        result = get_denominacion("30712505873")
    assert result == "CIGARS SONS S.R.L."


def test_get_denominacion_not_found():
    with patch("scraper.requests.get", return_value=_make_response(NOT_FOUND_HTML)):
        result = get_denominacion("99999999999")
    assert result == "NO ENCONTRADO"


def test_get_denominacion_network_error_retries_and_returns_empty():
    import requests as req
    with patch("scraper.requests.get", side_effect=req.RequestException("timeout")):
        result = get_denominacion("30712505873")
    assert result == ""


def test_get_denominacion_passes_cuit_in_query():
    with patch("scraper.requests.get", return_value=_make_response(NOT_FOUND_HTML)) as mock_get:
        get_denominacion("20123456789")
    call_args = mock_get.call_args
    assert "20123456789" in call_args[0][0] or "20123456789" in str(call_args)
```

- [ ] **Step 2: Correr tests para verificar que fallan**

```bash
pytest tests/test_scraper.py -v
```

Salida esperada: `ERROR` o `ModuleNotFoundError: No module named 'scraper'`

- [ ] **Step 3: Implementar `scraper.py`**

```python
import time
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.cuitonline.com/search.php"
DELAY_SECONDS = 0.5


def get_denominacion(cuit: str) -> str:
    """
    Busca la denominación de un CUIT en cuitonline.com.
    Retorna el nombre, "NO ENCONTRADO" si no existe, o "" si hay error de red.
    """
    url = f"{BASE_URL}?q={cuit}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException:
        # Reintento único
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except requests.RequestException:
            return ""

    soup = BeautifulSoup(response.text, "html.parser")
    tag = soup.find("a", class_="denominacion")
    if tag is None:
        return "NO ENCONTRADO"

    time.sleep(DELAY_SECONDS)
    return tag.get_text(strip=True)
```

- [ ] **Step 4: Correr tests para verificar que pasan**

```bash
pytest tests/test_scraper.py -v
```

Salida esperada:
```
PASSED tests/test_scraper.py::test_get_denominacion_found
PASSED tests/test_scraper.py::test_get_denominacion_not_found
PASSED tests/test_scraper.py::test_get_denominacion_network_error_retries_and_returns_empty
PASSED tests/test_scraper.py::test_get_denominacion_passes_cuit_in_query
4 passed
```

- [ ] **Step 5: Commit**

```bash
git add scraper.py tests/test_scraper.py
git commit -m "feat: scraper para cuitonline.com con retry y selector a.denominacion"
```

---

## Task 3: Procesador de Excel

**Files:**
- Create: `excel.py`
- Create: `tests/test_excel.py`

### Estructura del Excel real
- Fila 13: encabezados (`CUIT\nDonante/\nDonatario` en col A, `Denominación` en col B)
- Fila 14: vacía
- Fila 15+: datos. CUIT como entero en col A, denominación en col B (puede ser None)
- Solo se escriben celdas donde col B es `None` o string vacío

- [ ] **Step 1: Escribir tests que fallan**

Crear `tests/test_excel.py`:

```python
import io
from unittest.mock import patch
import openpyxl
from excel import procesar_excel


def _make_workbook(rows: list) -> bytes:
    """
    Crea un workbook mínimo con encabezados en fila 13 y datos desde fila 15.
    rows: lista de (cuit, denominacion) para insertar desde fila 15.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws["A13"] = "CUIT\nDonante/\nDonatario"
    ws["B13"] = "Denominación"
    for i, (cuit, denom) in enumerate(rows):
        row = 15 + i
        ws.cell(row=row, column=1, value=cuit)
        ws.cell(row=row, column=2, value=denom)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_fills_empty_denominacion():
    file_bytes = _make_workbook([(20123456789, None)])
    with patch("excel.get_denominacion", return_value="PEREZ JUAN"):
        result = procesar_excel(file_bytes)
    wb = openpyxl.load_workbook(io.BytesIO(result))
    ws = wb.active
    assert ws.cell(15, 2).value == "PEREZ JUAN"


def test_does_not_overwrite_existing_denominacion():
    file_bytes = _make_workbook([(30712505873, "CIGARS SONS S.R.L.")])
    with patch("excel.get_denominacion") as mock_get:
        result = procesar_excel(file_bytes)
    mock_get.assert_not_called()
    wb = openpyxl.load_workbook(io.BytesIO(result))
    ws = wb.active
    assert ws.cell(15, 2).value == "CIGARS SONS S.R.L."


def test_skips_row_with_empty_cuit():
    file_bytes = _make_workbook([(None, None)])
    with patch("excel.get_denominacion") as mock_get:
        result = procesar_excel(file_bytes)
    mock_get.assert_not_called()


def test_converts_integer_cuit_to_string():
    file_bytes = _make_workbook([(20123456789, None)])
    with patch("excel.get_denominacion", return_value="GARCIA") as mock_get:
        procesar_excel(file_bytes)
    mock_get.assert_called_once_with("20123456789")


def test_preserves_other_columns():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws["A13"] = "CUIT\nDonante/\nDonatario"
    ws["B13"] = "Denominación"
    ws.cell(15, 1, 20123456789)
    ws.cell(15, 2, None)
    ws.cell(15, 3, "Valor columna C")
    ws.cell(15, 4, 42)
    buf = io.BytesIO()
    wb.save(buf)
    file_bytes = buf.getvalue()

    with patch("excel.get_denominacion", return_value="GARCIA"):
        result = procesar_excel(file_bytes)

    wb2 = openpyxl.load_workbook(io.BytesIO(result))
    ws2 = wb2.active
    assert ws2.cell(15, 3).value == "Valor columna C"
    assert ws2.cell(15, 4).value == 42
```

- [ ] **Step 2: Correr tests para verificar que fallan**

```bash
pytest tests/test_excel.py -v
```

Salida esperada: `ModuleNotFoundError: No module named 'excel'`

- [ ] **Step 3: Implementar `excel.py`**

```python
import io
import openpyxl
from scraper import get_denominacion

HEADER_ROW = 13
DATA_START_ROW = 15
CUIT_COL = 1
DENOM_COL = 2


def procesar_excel(file_bytes: bytes) -> bytes:
    """
    Lee el workbook, completa columna B (Denominación) para filas donde:
    - col A (CUIT) tiene valor
    - col B está vacía
    Devuelve los bytes del workbook modificado.
    """
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes))
    ws = wb.active

    for row in range(DATA_START_ROW, ws.max_row + 1):
        cuit_val = ws.cell(row, CUIT_COL).value
        denom_val = ws.cell(row, DENOM_COL).value

        if not cuit_val:
            continue
        if denom_val and str(denom_val).strip():
            continue

        cuit_str = str(int(cuit_val))
        denominacion = get_denominacion(cuit_str)
        ws.cell(row, DENOM_COL).value = denominacion

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()
```

- [ ] **Step 4: Correr tests para verificar que pasan**

```bash
pytest tests/test_excel.py -v
```

Salida esperada:
```
PASSED tests/test_excel.py::test_fills_empty_denominacion
PASSED tests/test_excel.py::test_does_not_overwrite_existing_denominacion
PASSED tests/test_excel.py::test_skips_row_with_empty_cuit
PASSED tests/test_excel.py::test_converts_integer_cuit_to_string
PASSED tests/test_excel.py::test_preserves_other_columns
5 passed
```

- [ ] **Step 5: Correr todos los tests**

```bash
pytest -v
```

Salida esperada: `9 passed`

- [ ] **Step 6: Commit**

```bash
git add excel.py tests/test_excel.py
git commit -m "feat: procesador Excel que completa Denominacion solo en celdas vacías"
```

---

## Task 4: Servidor FastAPI

**Files:**
- Create: `main.py`

- [ ] **Step 1: Implementar `main.py`**

```python
from pathlib import Path
import io
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from excel import procesar_excel

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
    try:
        resultado = procesar_excel(file_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando el archivo: {e}")

    filename = file.filename.replace(".xlsx", "_completado.xlsx")
    return StreamingResponse(
        io.BytesIO(resultado),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

- [ ] **Step 2: Levantar el servidor**

```bash
uvicorn main:app --reload
```

Salida esperada:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

- [ ] **Step 3: Verificar que el servidor responde**

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/
```

Salida esperada: `200` (aunque el HTML aún no existe, debería devolver 500 o 404 — se resuelve en Task 5)

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat: FastAPI server con endpoint POST /procesar y serve de index.html"
```

---

## Task 5: Frontend HTML

**Files:**
- Create: `static/index.html`

- [ ] **Step 1: Crear `static/index.html`**

```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Completar Denominaciones CUIT</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: Arial, sans-serif;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      background: #f0f2f5;
    }
    .card {
      background: white;
      border-radius: 8px;
      padding: 40px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.1);
      width: 100%;
      max-width: 480px;
      text-align: center;
    }
    h1 { font-size: 1.4rem; margin-bottom: 8px; color: #1a1a1a; }
    p.subtitle { color: #666; font-size: 0.9rem; margin-bottom: 28px; }
    .drop-zone {
      border: 2px dashed #ccc;
      border-radius: 6px;
      padding: 32px;
      cursor: pointer;
      margin-bottom: 20px;
      transition: border-color 0.2s;
    }
    .drop-zone:hover { border-color: #4a90e2; }
    .drop-zone.has-file { border-color: #27ae60; background: #f0fff4; }
    .drop-zone p { color: #888; font-size: 0.9rem; }
    .drop-zone p.filename { color: #27ae60; font-weight: bold; }
    input[type="file"] { display: none; }
    button {
      width: 100%;
      padding: 12px;
      background: #4a90e2;
      color: white;
      border: none;
      border-radius: 6px;
      font-size: 1rem;
      cursor: pointer;
      transition: background 0.2s;
    }
    button:hover:not(:disabled) { background: #357abd; }
    button:disabled { background: #aaa; cursor: not-allowed; }
    #status {
      margin-top: 16px;
      font-size: 0.9rem;
      color: #555;
      min-height: 20px;
    }
    #status.error { color: #e74c3c; }
    #status.success { color: #27ae60; }
  </style>
</head>
<body>
  <div class="card">
    <h1>Completar Denominaciones</h1>
    <p class="subtitle">Subí el Excel con CUITs en columna A — se completan las denominaciones vacías en columna B.</p>

    <div class="drop-zone" id="dropZone">
      <p id="dropText">Hacé clic o arrastrá un archivo .xlsx aquí</p>
      <input type="file" id="fileInput" accept=".xlsx">
    </div>

    <button id="btn" disabled>Procesar</button>
    <div id="status"></div>
  </div>

  <script>
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const dropText = document.getElementById('dropText');
    const btn = document.getElementById('btn');
    const status = document.getElementById('status');

    let selectedFile = null;

    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropZone.style.borderColor = '#4a90e2';
    });

    dropZone.addEventListener('dragleave', () => {
      dropZone.style.borderColor = selectedFile ? '#27ae60' : '#ccc';
    });

    dropZone.addEventListener('drop', (e) => {
      e.preventDefault();
      const file = e.dataTransfer.files[0];
      if (file && file.name.endsWith('.xlsx')) setFile(file);
      else setStatus('Solo se aceptan archivos .xlsx', 'error');
    });

    fileInput.addEventListener('change', () => {
      if (fileInput.files[0]) setFile(fileInput.files[0]);
    });

    function setFile(file) {
      selectedFile = file;
      dropZone.classList.add('has-file');
      dropText.textContent = file.name;
      dropText.className = 'filename';
      btn.disabled = false;
      setStatus('');
    }

    function setStatus(msg, type = '') {
      status.textContent = msg;
      status.className = type;
    }

    btn.addEventListener('click', async () => {
      if (!selectedFile) return;

      btn.disabled = true;
      setStatus('Procesando... esto puede tardar varios minutos según la cantidad de CUITs.', '');

      const formData = new FormData();
      formData.append('file', selectedFile);

      try {
        const response = await fetch('/procesar', { method: 'POST', body: formData });

        if (!response.ok) {
          const err = await response.json();
          throw new Error(err.detail || 'Error desconocido');
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const disposition = response.headers.get('Content-Disposition') || '';
        const match = disposition.match(/filename="(.+)"/);
        a.download = match ? match[1] : 'resultado.xlsx';
        a.click();
        URL.revokeObjectURL(url);

        setStatus('Listo. El archivo se descargó automáticamente.', 'success');
      } catch (err) {
        setStatus('Error: ' + err.message, 'error');
      } finally {
        btn.disabled = false;
      }
    });
  </script>
</body>
</html>
```

- [ ] **Step 2: Verificar que el servidor sirve el HTML**

Con uvicorn corriendo, abrir `http://localhost:8000` en el navegador. Debe verse la UI con el drop zone y el botón "Procesar".

- [ ] **Step 3: Commit**

```bash
git add static/index.html
git commit -m "feat: UI web para subir Excel y descargar resultado completado"
```

---

## Task 6: Verificación end-to-end

- [ ] **Step 1: Correr todos los tests unitarios**

```bash
pytest -v
```

Salida esperada: `9 passed`

- [ ] **Step 2: Levantar servidor**

```bash
uvicorn main:app --reload
```

- [ ] **Step 3: Subir el Excel real desde el navegador**

1. Abrir `http://localhost:8000`
2. Seleccionar `Aplicativo Donaciones Bal2425 fund CLS hoja 6 xlsx.xlsx`
3. Hacer clic en "Procesar"
4. Esperar (hay ~3000 filas, puede tardar bastante)
5. Verificar que se descarga `Aplicativo Donaciones Bal2425 fund CLS hoja 6 xlsx_completado.xlsx`

- [ ] **Step 4: Verificar el resultado**

Abrir el Excel descargado y verificar:
- Columna A sin cambios
- Columna B completada para CUITs que antes estaban vacíos (ej. fila 18: CUIT 20410053900 debe tener nombre)
- Columna B sin cambios donde ya tenía valor (ej. fila 15: "casella fabiana" intacto)
- Todas las demás columnas (C en adelante) sin cambios
- CUITs no encontrados muestran "NO ENCONTRADO"

- [ ] **Step 5: Commit final**

```bash
git add .
git commit -m "chore: verificación end-to-end completada"
```

---

## Notas de implementación

- **Timeout por fila**: con DELAY_SECONDS=0.5 y ~3000 filas, el procesamiento puede tardar ~25 minutos. El endpoint es síncrono, el navegador espera. Si esto es un problema, se puede agregar WebSocket para progreso en una iteración futura.
- **CUITs duplicados**: el scraper hace un request por cada fila, incluso si hay CUITs repetidos. Para optimizar, se puede cachear resultados (dict en memoria). No incluido por YAGNI — agregar si la performance lo requiere.
- **Advertencia de openpyxl**: "Data Validation extension is not supported" es un warning conocido y no afecta el funcionamiento.

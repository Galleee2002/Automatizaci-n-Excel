import io
import base64
import logging
import openpyxl
from scraper import get_denominacion

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")

HEADER_ROW = 13
DATA_START_ROW = 15
CUIT_COL = 1
DENOM_COL = 2


def _cuit_str(val) -> str:
    """Convierte el valor de celda CUIT a string limpio."""
    raw = str(val).strip()
    # Si Excel guardó el número como float (ej. 20123456789.0) lo normalizamos
    if raw.endswith(".0") and raw[:-2].isdigit():
        return raw[:-2]
    return raw


def procesar_excel(file_bytes: bytes) -> bytes:
    """
    Lee el workbook, completa columna B (Denominación) para filas donde:
    - col A (CUIT) tiene valor
    - col B está vacía
    Devuelve los bytes del workbook modificado.
    """
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes))
    ws = wb.active

    logger.debug("Hoja activa: %s | max_row reportado: %d", ws.title, ws.max_row)

    for row in range(DATA_START_ROW, ws.max_row + 1):
        cuit_val = ws.cell(row, CUIT_COL).value
        denom_val = ws.cell(row, DENOM_COL).value

        if not cuit_val:
            continue
        if denom_val and str(denom_val).strip():
            continue

        cuit_str = _cuit_str(cuit_val)
        denominacion = get_denominacion(cuit_str)
        ws.cell(row, DENOM_COL).value = denominacion

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()


def procesar_excel_progreso(file_bytes: bytes):
    """
    Generador que procesa el workbook y emite eventos de progreso.
    Yields dicts con 'tipo': 'progreso' | 'listo' | 'error'.
    Evento final 'listo' incluye el archivo codificado en base64.
    """
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes))
    ws = wb.active

    logger.debug("Hoja activa: '%s' | max_row: %d", ws.title, ws.max_row)

    filas = []
    for row in range(DATA_START_ROW, ws.max_row + 1):
        cuit_val = ws.cell(row, CUIT_COL).value
        denom_val = ws.cell(row, DENOM_COL).value
        if not cuit_val:
            continue
        if denom_val and str(denom_val).strip():
            logger.debug("Fila %d: CUIT %s ya tiene denominación '%s', se omite", row, cuit_val, denom_val)
            continue
        filas.append((row, _cuit_str(cuit_val)))

    total = len(filas)
    logger.debug("Filas a procesar: %d", total)

    escritas = 0
    for i, (row, cuit_str) in enumerate(filas):
        denom = get_denominacion(cuit_str)
        ws.cell(row, DENOM_COL).value = denom
        escritas += 1
        logger.debug("Fila %d: CUIT %s → '%s'", row, cuit_str, denom)
        yield {"tipo": "progreso", "actual": i + 1, "total": total, "cuit": cuit_str, "denom": denom}

    logger.debug("Total celdas escritas: %d", escritas)

    output = io.BytesIO()
    wb.save(output)
    file_size = output.tell()
    logger.debug("Archivo guardado: %d bytes", file_size)
    yield {"tipo": "listo", "archivo_b64": base64.b64encode(output.getvalue()).decode()}

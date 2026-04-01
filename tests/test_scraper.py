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

from unittest.mock import patch, MagicMock
import requests as req
from scraper import get_denominacion, resolve_cuits_parallel


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


def _session_patch():
    return patch("scraper.requests.Session")


def test_get_denominacion_found():
    mock_resp = _make_response(FOUND_HTML)
    with _session_patch() as MS:
        inst = MagicMock()
        inst.get.return_value = mock_resp
        MS.return_value = inst
        result = get_denominacion("30712505873")
    assert result == "CIGARS SONS S.R.L."


def test_get_denominacion_not_found():
    mock_resp = _make_response(NOT_FOUND_HTML)
    with _session_patch() as MS:
        inst = MagicMock()
        inst.get.return_value = mock_resp
        MS.return_value = inst
        result = get_denominacion("99999999999")
    assert result == "NO ENCONTRADO"


def test_get_denominacion_network_error_retries_and_returns_empty():
    with _session_patch() as MS:
        inst = MagicMock()
        inst.get.side_effect = req.RequestException("timeout")
        MS.return_value = inst
        result = get_denominacion("30712505873")
    assert result == "NO ENCONTRADO"


def test_get_denominacion_passes_cuit_in_query():
    mock_resp = _make_response(NOT_FOUND_HTML)
    with _session_patch() as MS:
        inst = MagicMock()
        inst.get.return_value = mock_resp
        MS.return_value = inst
        get_denominacion("20123456789")
    call_args = inst.get.call_args
    url = call_args[0][0] if call_args[0] else call_args[1].get("url", "")
    assert "20123456789" in url


def test_resolve_cuits_parallel_empty():
    assert resolve_cuits_parallel([]) == {}


def test_resolve_cuits_parallel_uses_fetch(monkeypatch):
    def fake_fetch(cuit, session):
        return f"NAME_{cuit}"

    monkeypatch.setattr("scraper.fetch_denominacion", fake_fetch)
    out = resolve_cuits_parallel(["11", "22"], max_workers=2)
    assert out == {"11": "NAME_11", "22": "NAME_22"}

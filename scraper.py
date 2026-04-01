import threading
from concurrent.futures import ThreadPoolExecutor

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter

BASE_URL = "https://www.cuitonline.com/search.php"
PARALLEL_WORKERS = 60
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

_thread_local = threading.local()


def _thread_session() -> requests.Session:
    s = getattr(_thread_local, "session", None)
    if s is None:
        s = requests.Session()
        s.headers.update(HEADERS)
        adapter = HTTPAdapter(
            pool_connections=PARALLEL_WORKERS,
            pool_maxsize=PARALLEL_WORKERS,
            max_retries=0,
        )
        s.mount("https://", adapter)
        _thread_local.session = s
    return s


def _parse_denominacion_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    tag = soup.find("a", class_="denominacion")
    if tag is None:
        return "NO ENCONTRADO"
    return tag.get_text(strip=True)


def fetch_denominacion(cuit: str, session: requests.Session) -> str:
    url = f"{BASE_URL}?q={cuit}"
    for _ in range(2):
        try:
            response = session.get(url, timeout=12)
            response.raise_for_status()
            return _parse_denominacion_html(response.text)
        except requests.RequestException:
            continue
    return "NO ENCONTRADO"


def resolve_cuits_parallel(
    cuits: list[str],
    max_workers: int = PARALLEL_WORKERS,
) -> dict[str, str]:
    if not cuits:
        return {}
    workers = min(max_workers, len(cuits))

    def task(c: str) -> tuple[str, str]:
        return c, fetch_denominacion(c, _thread_session())

    with ThreadPoolExecutor(max_workers=workers) as ex:
        return dict(ex.map(task, cuits))


def get_denominacion(cuit: str) -> str:
    session = requests.Session()
    session.headers.update(HEADERS)
    session.mount(
        "https://",
        HTTPAdapter(pool_connections=2, pool_maxsize=2, max_retries=0),
    )
    return fetch_denominacion(cuit, session)

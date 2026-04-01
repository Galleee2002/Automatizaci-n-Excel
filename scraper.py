import time
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.cuitonline.com/search.php"
DELAY_SECONDS = 0.5
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def get_denominacion(cuit: str) -> str:
    """
    Busca la denominación de un CUIT en cuitonline.com.
    Retorna el nombre encontrado, o "NO ENCONTRADO" si no existe o hay error de red.
    """
    url = f"{BASE_URL}?q={cuit}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
    except requests.RequestException:
        # Reintento único
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
        except requests.RequestException:
            return "NO ENCONTRADO"

    soup = BeautifulSoup(response.text, "html.parser")
    tag = soup.find("a", class_="denominacion")
    if tag is None:
        return "NO ENCONTRADO"

    time.sleep(DELAY_SECONDS)
    return tag.get_text(strip=True)

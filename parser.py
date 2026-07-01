"""
Поиск и загрузка треков с eu.hitmoz.com.

Функции синхронные (requests) — вызывай их из бота через asyncio.to_thread,
чтобы не блокировать event loop.

Прокси: если задать переменную окружения PROXY_URL (http/https/socks5), все запросы
пойдут через неё. Это нужно на сервере — сайт отдаёт 403 с IP дата-центров.
Пример: PROXY_URL=socks5://user:pass@1.2.3.4:1080
"""
import os
import re
import time
import tempfile

import requests
from bs4 import BeautifulSoup

BASE = "https://eu.hitmoz.com"
PROXY_URL = os.getenv("PROXY_URL")

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


def _session(extra_headers: dict) -> requests.Session:
    """Готовая сессия с браузерными заголовками и (опционально) прокси."""
    s = requests.Session()
    s.headers.update(extra_headers)
    if PROXY_URL:
        s.proxies.update({"http": PROXY_URL, "https": PROXY_URL})
    return s


def _abs(url: str) -> str:
    return BASE + url if url.startswith("/") else url


def search_and_get_download_link(query: str):
    """Ищет трек и возвращает прямую ссылку на MP3 (или None)."""
    if not query or not query.strip():
        print("Пустой запрос")
        return None

    try:
        search_url = f"{BASE}/search?q={requests.utils.quote(query)}"
        headers = {
            "User-Agent": _BROWSER_UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": f"{BASE}/",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        time.sleep(1)
        session = _session(headers)
        response = session.get(search_url, timeout=15)

        if response.status_code != 200:
            print(f"Ошибка доступа к сайту: {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        # 1) прямые ссылки на .mp3
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            if href.endswith(".mp3"):
                print(f"Найдена mp3-ссылка: {_abs(href)}")
                return _abs(href)

        # 2) data-атрибуты
        for tag in soup.find_all(True):
            for attr in ("data-url", "data-link", "data-download", "data-src", "data-mp3"):
                data_url = tag.get(attr, "")
                if data_url.endswith(".mp3"):
                    print(f"Найдена mp3-ссылка в data-атрибуте: {_abs(data_url)}")
                    return _abs(data_url)

        # 3) ссылки внутри <script>
        for script in soup.find_all("script"):
            if script.string:
                for match in re.findall(r'["\']([^"\']+\.mp3)["\']', script.string):
                    print(f"Найдена mp3-ссылка в JS: {_abs(match)}")
                    return _abs(match)

        print("Ничего не найдено")
        return None

    except Exception as e:
        print(f"Ошибка парсинга: {e}")
        return None


def download_mp3_to_temp(mp3_url: str, track_name: str):
    """Скачивает MP3 во временную папку и возвращает путь к файлу (или None)."""
    try:
        headers = {
            "User-Agent": _BROWSER_UA,
            "Accept": "audio/webm,audio/ogg,audio/wav,audio/*;q=0.9,application/ogg;q=0.7,video/*;q=0.6,*/*;q=0.5",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "identity",
            "Referer": f"{BASE}/",
            "Origin": BASE,
            "Connection": "keep-alive",
        }
        print(f"Скачиваю трек: {mp3_url}")
        session = _session(headers)

        # «Разогрев» — заходим на главную, затем качаем без Range (чтобы был 200)
        session.get(f"{BASE}/", timeout=10)
        time.sleep(0.5)
        response = session.get(mp3_url, timeout=60, stream=True)

        if response.status_code not in (200, 206):
            print(f"Ошибка скачивания: {response.status_code}")
            if response.status_code == 403:
                print("Пробую альтернативный подход…")
                alt = _session({
                    "User-Agent": _BROWSER_UA,
                    "Accept": "*/*",
                    "Accept-Language": "ru-RU,ru;q=0.9",
                    "Accept-Encoding": "identity",
                    "Referer": mp3_url,
                    "Connection": "keep-alive",
                })
                alt.get(f"{BASE}/", timeout=10)
                time.sleep(0.5)
                response = alt.get(mp3_url, timeout=60, stream=True)
                if response.status_code not in (200, 206):
                    print(f"Альтернативный подход тоже не сработал: {response.status_code}")
                    return None
            else:
                return None

        safe_name = re.sub(r'[<>:"/\\|?*]', "", track_name).strip() or "track"
        file_path = os.path.join(tempfile.gettempdir(), f"{safe_name}.mp3")

        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        if os.path.getsize(file_path) > 0:
            print(f"Трек сохранён: {file_path} ({os.path.getsize(file_path)} байт)")
            return file_path

        print("Файл пустой")
        os.remove(file_path)
        return None

    except Exception as e:
        print(f"Ошибка при скачивании трека: {e}")
        return None

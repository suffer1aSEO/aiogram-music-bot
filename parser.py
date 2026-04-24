import requests
from bs4 import BeautifulSoup
import re
import time
import os
import tempfile


def search_and_get_download_link(query):
    """
    Ищет трек на eu.hitmoz.com и возвращает прямую ссылку на MP3.
    """
    if not query or not query.strip():
        print("Пустой запрос")
        return None

    try:
        search_url = f"https://eu.hitmoz.com/search?q={requests.utils.quote(query)}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://eu.hitmoz.com/",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Upgrade-Insecure-Requests": "1",
        }

        time.sleep(1)

        session = requests.Session()
        session.headers.update(headers)

        response = session.get(search_url, timeout=15)

        if response.status_code != 200:
            print(f"Ошибка доступа к сайту: {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        # Ищем прямые ссылки на .mp3
        all_links = soup.find_all("a", href=True)
        for link in all_links:
            href = link.get("href", "")
            if href.endswith(".mp3"):
                if href.startswith("/"):
                    href = "https://eu.hitmoz.com" + href
                print(f"Найдена mp3-ссылка: {href}")
                return href


        for tag in soup.find_all(True):
            for attr in ["data-url", "data-link", "data-download", "data-src", "data-mp3"]:
                data_url = tag.get(attr, "")
                if data_url.endswith(".mp3"):
                    if data_url.startswith("/"):
                        data_url = "https://eu.hitmoz.com" + data_url
                    print(f"Найдена mp3-ссылка в data-атрибуте: {data_url}")
                    return data_url

        scripts = soup.find_all("script")
        for script in scripts:
            if script.string:
                matches = re.findall(r'["\']([^"\']+\.mp3)["\']', script.string)
                for match in matches:
                    if match.startswith("/"):
                        match = "https://eu.hitmoz.com" + match
                    print(f"Найдена mp3-ссылка в JS: {match}")
                    return match

        print("Ничего не найдено")
        return None

    except Exception as e:
        print(f"Ошибка парсинга: {e}")
        return None


def download_mp3_to_temp(mp3_url, track_name):
    """
    Скачивает MP3-файл во временную папку и возвращает путь к файлу.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "audio/webm,audio/ogg,audio/wav,audio/*;q=0.9,application/ogg;q=0.7,video/*;q=0.6,*/*;q=0.5",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "identity",
            "Referer": "https://eu.hitmoz.com/",
            "Origin": "https://eu.hitmoz.com",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "audio",
            "Sec-Fetch-Mode": "no-cors",
            "Sec-Fetch-Site": "same-origin",
            # УБИРАЕМ Range, чтобы сервер вернул 200, а не 206
        }

        print(f"Скачиваю трек: {mp3_url}")

        session = requests.Session()
        session.headers.update(headers)

        # Разогрев — заходим на главную
        session.get("https://eu.hitmoz.com/", timeout=10)
        time.sleep(0.5)

        # Качаем mp3 БЕЗ Range-заголовка
        response = session.get(mp3_url, timeout=60, stream=True)

        # ============================================================
        # ВАЖНО: Принимаем и 200, и 206 как успех
        # ============================================================
        if response.status_code not in [200, 206]:
            print(f"Ошибка скачивания: {response.status_code}")

            # Пробуем вообще без Referer и Origin
            if response.status_code == 403:
                print("Пробую альтернативный подход...")
                alt_headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    "Accept": "*/*",
                    "Accept-Language": "ru-RU,ru;q=0.9",
                    "Accept-Encoding": "identity",
                    "Referer": mp3_url,
                    "Connection": "keep-alive",
                }

                session2 = requests.Session()
                session2.headers.update(alt_headers)
                session2.get("https://eu.hitmoz.com/", timeout=10)
                time.sleep(0.5)

                response = session2.get(mp3_url, timeout=60, stream=True)

                if response.status_code not in [200, 206]:
                    print(f"Альтернативный подход тоже не сработал: {response.status_code}")
                    return None

        # Создаём временный файл
        temp_dir = tempfile.gettempdir()
        safe_name = re.sub(r'[<>:"/\\|?*]', '', track_name)
        file_path = os.path.join(temp_dir, f"{safe_name}.mp3")

        # Сохраняем файл
        downloaded = 0

        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

        # Проверяем, что файл не пустой
        file_size = os.path.getsize(file_path)
        if file_size > 0:
            print(f"Трек сохранён: {file_path} (размер: {file_size} байт)")
            return file_path
        else:
            print("Файл пустой")
            os.remove(file_path)
            return None

    except Exception as e:
        print(f"Ошибка при скачивании трека: {e}")
        return None
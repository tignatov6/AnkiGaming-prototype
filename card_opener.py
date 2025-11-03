import http.server
import socketserver
import webbrowser
import json
import random
import time
import requests
import threading
import pygetwindow as pw
from screeninfo import get_monitors
import pyautogui
import win32gui
import win32con
import base64
import mimetypes
import urllib.parse
import sys

# --- Настройки ---
PORT = 8000
ANKI_CONNECT_URL = "http://localhost:8765"
ANKI_CONNECT_VERSION = 6
HEARTBEAT_TIMEOUT = 1 # Секунд без "пульса" до повторного открытия

# --- Глобальные переменные для обмена данными между потоками ---
last_heartbeat_time = time.time()
card_answered = False
httpd_server = None
app_running = True
page_theme = 'system'

def invoke_anki_connect(action, **params):
    """Отправляет запрос к AnkiConnect."""
    payload = {"action": action, "version": ANKI_CONNECT_VERSION, "params": params}
    try:
        response = requests.post(ANKI_CONNECT_URL, data=json.dumps(payload))
        response.raise_for_status()
        response_json = response.json()
        if response_json.get('error'):
            print(f"AnkiConnect Error: {response_json['error']}")
            return None
        return response_json.get('result')
    except requests.exceptions.RequestException as e:
        print(f"Connection Error: {e}")
        print('-' * 50)
        print('Check if Anki is open and if the AnkiConnect extension is installed and enabled.')
        return None

def create_html(card_info, web_page_theme = 'system'):
    """Создает HTML-страницу с механизмом "пульса" и поддержкой тем.
        web_page_theme: 'system'/'dark'/'light'
    """

    # Определяем, какой атрибут темы добавить в тег <html>
    # Для 'system' атрибут не добавляется, чтобы браузер сам решал по настройкам ОС
    theme_attribute = f"data-theme='{web_page_theme}'" if web_page_theme in ['light', 'dark'] else ''

    # --- НОВЫЙ БЛОК: СТИЛИ ДЛЯ ТЕМ ---
    # Определяем стили с использованием CSS-переменных для легкой смены темы
    theme_styles = """
        /* 1. Сообщаем браузеру, что страница поддерживает темы, и задаем переменные для светлой темы по умолчанию */
        :root {
            color-scheme: light dark;

            --bg-color: #f0f0f0;
            --text-color: #111111;
            --card-bg: #ffffff;
            --border-color: #dddddd;
            --button-bg: #efefef;
            --button-text-color: #111111;
            --button-hover-bg: #dcdcdc;
        }

        /* 2. Определяем переменные для темной темы */
        @media (prefers-color-scheme: dark) {
            :root {
                --bg-color: #121212;
                --text-color: #eeeeee;
                --card-bg: #1e1e1e;
                --border-color: #444444;
                --button-bg: #333333;
                --button-text-color: #eeeeee;
                --button-hover-bg: #555555;
            }
        }

        /* 3. Принудительно применяем темы, если задан атрибут data-theme */
        html[data-theme='dark'] {
            --bg-color: #121212;
            --text-color: #eeeeee;
            --card-bg: #1e1e1e;
            --border-color: #444444;
            --button-bg: #333333;
            --button-text-color: #eeeeee;
            --button-hover-bg: #555555;
        }
        html[data-theme='light'] {
            --bg-color: #f0f0f0;
            --text-color: #111111;
            --card-bg: #ffffff;
            --border-color: #dddddd;
            --button-bg: #efefef;
            --button-text-color: #111111;
            --button-hover-bg: #dcdcdc;
        }

        /* 4. Применяем переменные к элементам страницы */
        body { 
            background-color: var(--bg-color);
            color: var(--text-color);
        }
        .card {
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
        }
        #answer {
             border-top: 1px solid var(--border-color);
        }
        button {
            background-color: var(--button-bg);
            color: var(--button-text-color);
            border: 1px solid var(--border-color);
            border-radius: 5px;
        }
        button:hover {
            background-color: var(--button-hover-bg);
        }
        button:disabled {
            opacity: 0.7;
            cursor: default;
        }
    """
    
    # --- СТРАНИЦА ОШИБКИ ---
    if not card_info: 
        return f"""
        <!DOCTYPE html><html lang="ru" {theme_attribute}><head><meta charset="UTF-8">
        <title>AnkiGaming - Page - Ошибка</title>
        <style>
            {theme_styles} /* Вставляем стили тем */
            body {{ font-family: sans-serif; display: flex; justify-content: center; align-items: center; flex-direction: column; min-height: 100vh; text-align: center; }}
            button {{ margin-top: 20px; padding: 10px 20px; font-size: 16px; cursor: pointer; }}
        </style>
        </head><body>
        <h1>Карточка не найдена.</h1>
        <p>Возможно, в выбранной колоде нет карточек для повторения.</p>
        <button onclick="shutdown()">Выключить "AnkiGaming - Page"</button>
        <script>
            function shutdown() {{
                fetch('/shutdown').then(() => {{ setTimeout(() => window.close(), 100); }});
            }}
        </script>
        </body></html>
        """

    question_html = card_info['question']
    answer_html = card_info['answer']
    css = card_info['css']
    
    buttons_html = ""
    button_map = {1: "Снова", 2: "Трудно", 3: "Хорошо", 4: "Легко"}
    for ease_value in card_info.get('buttons', []):
        buttons_html += f'<button onclick="answerCardAndClose({ease_value})">{button_map[ease_value]}</button>'

    # --- ОСНОВНАЯ СТРАНИЦА ---
    html_template = f"""
    <!DOCTYPE html><html lang="ru" {theme_attribute}><head><meta charset="UTF-8">
    <title>AnkiGaming - Page</title>
    <style>
        /* Стили из карточки anki */
        {css} 

        /* Общие стили страницы */
        body {{ font-family: sans-serif; display: flex; justify-content: center; align-items: center; flex-direction: column; min-height: 100vh; text-align: center; margin: 0; }}
        .card {{ padding: 25px; border-radius: 10px; max-width: 800px; min-width: 500px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        #answer {{ display: none; margin-top: 20px; padding-top: 20px; }}
        #answer-buttons {{ display: none; margin-top: 20px; }}
        #show-answer-btn {{ margin-top: 20px; }}
        button {{ margin: 5px; padding: 10px 20px; font-size: 16px; cursor: pointer; }}

        /* Вставляем новые стили для тем */
        {theme_styles}
    </style>
    </head><body>
    <div class="card">
        <div id="question">{question_html}</div>
        <div id="answer">{answer_html}</div>
    </div>
    <button id="show-answer-btn" onclick="showAnswer()">Показать ответ</button>
    <div id="answer-buttons">{buttons_html}</div>
    <script>
        const heartbeatInterval = setInterval(() => {{
            fetch('/heartbeat').catch(err => console.error('Heartbeat failed:', err));
        }}, 50);

        function showAnswer() {{
            document.getElementById('question').style.display = 'none'; 
            document.getElementById('answer').style.display = 'block';
            document.getElementById('show-answer-btn').style.display = 'none';
            document.getElementById('answer-buttons').style.display = 'block';
        }}
        
        function answerCardAndClose(ease) {{
            clearInterval(heartbeatInterval);
            document.querySelectorAll('button').forEach(b => b.disabled = true);
            fetch('/answer', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ ease: ease }})
            }}).then(response => {{
                setTimeout(() => window.close(), 100);
            }});
        }}
    </script>
    </body></html>
    """
    return html_template

def get_monitor_from_mouse():
    """
    Определяет, на каком мониторе находится курсор мыши, используя
    библиотеки pyautogui и screeninfo. Не зависит от графического фреймворка.

    Возвращает:
        Объект screeninfo.Monitor, на котором находится курсор,
        или основной монитор, если определить не удалось.
    """
    try:
        mouse_x, mouse_y = pyautogui.position()
        monitors = get_monitors()

        for m in monitors:
            if m.x <= mouse_x < m.x + m.width and m.y <= mouse_y < m.y + m.height:
                return m
        
        primary_monitor = next((m for m in monitors if m.is_primary), None)
        return primary_monitor if primary_monitor else monitors[0]

    except Exception as e:
        print(f"Ошибка при определении монитора: {e}")
        return get_monitors()[0] if get_monitors() else None


def position_and_resize_window(window_title, target_monitor):
    """
    Находит окно по заголовку и перемещает его на целевой монитор,
    растягивая на весь экран. Работает в отдельном потоке.
    """
    
    try:
        win = None
        # --- НОВОЕ: Ждем появления окна до 5 секунд ---
        #print(f"Ожидание появления окна с заголовком: '{window_title}'...")
        for _ in range(50): # 50 попыток по 0.1 секунды
            windows = pw.getWindowsWithTitle(window_title)
            if windows:
                win = windows[0]
                #print("Окно найдено.")
                break
            time.sleep(0.1)
        # Ищем окно по его точному заголовку. getWindowsWithTitle возвращает список.
        
        if win:
            #print(f"Окно '{window_title}' найдено. Перемещение на монитор...")
            # Убираем возможность изменять размер и разворачивать стандартными средствами
            # Это делает его более похожим на полноэкранный режим
            hwnd = win._hWnd
            if not win.isMaximized:
                win.minimize()
                win.restore()
                win.maximize()
                win.moveTo(target_monitor.x, target_monitor.y)
                win.restore()
                win.moveTo(0, 0)
                win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
                time.sleep(0.25)
                win.minimize()
                win.restore()
                win.moveTo(target_monitor.x, target_monitor.y)
                win.maximize()
                win.restore()
                win.moveTo(0, 0)
                win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)

            # Перемещаем окно в верхний левый угол целевого монитора
            win.moveTo(target_monitor.x, target_monitor.y)
            
            # Растягиваем окно на всю ширину и высоту целевого монитора
            win.maximize()
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            #win.activate()
            #print("Перемещение и растягивание завершено.")
        else:
            # Этот блок кода вряд ли выполнится из-за обработки исключения IndexError
            print(f"Окно с заголовком '{window_title}' не найдено.")
            
    except IndexError:
        print(f"ОШИБКА: Не удалось найти окно с заголовком '{window_title}'. Убедитесь, что заголовок точен.")
    except Exception as e:
        print(f"Произошла непредвиденная ошибка: {e}")

def shutdown_server():
    """Безопасно останавливает сервер в отдельном потоке."""
    global app_running
    app_running = False
    if httpd_server:
        threading.Thread(target=httpd_server.shutdown).start()


# Создаем обработчик запросов, который будет обновлять время "пульса"
class HeartbeatHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        global last_heartbeat_time, page_theme
        
        # Декодируем путь, чтобы обработать имена файлов с пробелами или кириллицей
        decoded_path = urllib.parse.unquote(self.path)

        if decoded_path == '/shutdown':
            # Получили команду на выключение
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'Shutting down')
            shutdown_server() # Вызываем нашу новую функцию для остановки

        elif decoded_path == '/heartbeat':
            # Получили "пульс", обновляем время
            last_heartbeat_time = time.time()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
            
        elif decoded_path == '/':
            # Если это корневой запрос, отдаем HTML-страницу
            card_info = invoke_anki_connect('guiCurrentCard')
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            html_content = create_html(card_info,page_theme)
            self.wfile.write(html_content.encode('utf-8'))
            
        else:
            # --- НОВЫЙ БЛОК: ОБРАБОТКА МЕДИАФАЙЛОВ ---
            # Иначе, предполагаем, что это запрос медиафайла (картинки, звука и т.д.)
            try:
                # Убираем слэш в начале имени файла
                filename = decoded_path.lstrip('/')
                
                # Запрашиваем файл у AnkiConnect, он вернет его в формате base64
                media_data_base64 = invoke_anki_connect('retrieveMediaFile', filename=filename)

                if media_data_base64:
                    # Декодируем base64, чтобы получить бинарные данные файла
                    file_content = base64.b64decode(media_data_base64)
                    
                    # Определяем MIME-тип файла по его расширению (напр., 'image/png')
                    content_type, _ = mimetypes.guess_type(filename)
                    
                    self.send_response(200)
                    if content_type:
                        self.send_header("Content-type", content_type)
                    self.end_headers()
                    self.wfile.write(file_content)
                else:
                    # Если AnkiConnect не нашел файл, отправляем ошибку 404
                    self.send_error(404, f"File Not Found: {filename}")
            
            except Exception as e:
                print(f"Error serving media file {decoded_path}: {e}")
                self.send_error(500, "Internal Server Error")

    def do_POST(self):
        global card_answered # Убираем httpd_server, он здесь больше не нужен
        if self.path == '/answer':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            ease = json.loads(post_data).get('ease')
            
            invoke_anki_connect('guiShowAnswer')
            invoke_anki_connect('guiAnswerCard', ease=ease)
            
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')

            # <--- ИЗМЕНЕНИЕ: Просто устанавливаем флаг. Больше не вызываем shutdown() отсюда.
            card_answered = True

    def log_message(self, format, *args):
        # Отключаем логирование в консоль, чтобы не засорять вывод
        return

def open_card(web_page_theme='system',deck_name=None):
    global last_heartbeat_time, card_answered, httpd_server, app_running, page_theme
    page_theme = web_page_theme

    card_answered = False
    error=False

    # 1. Начинаем сессию в Anki
    if deck_name:
        random_deck = deck_name
    else:
        deck_names = invoke_anki_connect('deckNames')
        if not deck_names: return False
        random_deck = random.choice(deck_names)
    print(f"Запуск повторения в Anki для колоды: '{random_deck}'")
    invoke_anki_connect('guiDeckReview', name=random_deck)

    if not invoke_anki_connect('guiCurrentCard'):
        print("В колоде нет карточек для повторения. Завершение работы.")
        invoke_anki_connect('guiExit') # Закрываем окно Anki "Обзор"
        error = True

    # 2. Запускаем веб-сервер в отдельном потоке
    with socketserver.TCPServer(("", PORT), HeartbeatHandler) as httpd:
        httpd_server = httpd # Сохраняем экземпляр в глобальную переменную для доступа из обработчика
        server_thread = threading.Thread(target=httpd.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        url = f"http://127.0.0.1:{PORT}"
        print(f"Сервер запущен на {url}. Ожидание ответа...")
        webbrowser.open(url)
        for _ in range(2):
            for monitor in get_monitors():
                position_and_resize_window("AnkiGaming - Page", monitor)
        last_heartbeat_time = time.time()

        # 3. Основной цикл мониторинга в главном потоке
        while not card_answered:
            if not app_running:
                break

            time.sleep(HEARTBEAT_TIMEOUT) 
            if time.time() - last_heartbeat_time > HEARTBEAT_TIMEOUT:
                # <--- УЛУЧШЕНИЕ: Добавим проверку, чтобы не открывать окно, если уже ответили
                if not card_answered and not error:
                    #print("Браузер был закрыт неправильно! Открываю заново...")
                    webbrowser.open(url)
                    last_heartbeat_time = time.time()
            elif not card_answered: # Доп. проверка, чтобы избежать ошибки "окно не найдено"
                position_and_resize_window("AnkiGaming - Page", get_monitor_from_mouse())

        # 4. Если мы вышли из цикла, значит, ответ получен.
        print("Ответ получен. Ожидание завершения работы сервера...")
        
        httpd.shutdown()
        server_thread.join()
    
    print("Сервер остановлен. Скрипт успешно завершил свою работу.")

    return app_running

if __name__ == "__main__":
    open_card()
import subprocess
import threading
import pyautogui
import time
import glob
import sys
import os

import card_opener 
from TrayIcon import SysTrayIcon
from config import Config

TEMPLATES_DIR = "templates"
CONFIG = Config()
shutdown_event = threading.Event()


def edit_config(systray_icon=None):
    """Эта функция находится в основном приложении. Мы вызовем ее из трея."""
    print("Открываем config.yaml")
    subprocess.run(["notepad.exe", CONFIG.config_file_path])
    CONFIG.update_config()

def on_quit_callback(systray_icon=None):
    """Эта функция вызывается, когда трей готовится к выходу."""
    print('Выход из приложения...')
    shutdown_event.set() # Посылаем сигнал основному потоку на завершение
    card_opener.shutdown_server()


def on_death():
    print("Экран смерти обнаружен! Выполняю действие...")
    print(f"CONFIG.web_page_theme: {CONFIG.web_page_theme}")
    print(f"CONFIG.deck_name: {CONFIG.deck_name}")
    if not card_opener.open_card(CONFIG.web_page_theme,CONFIG.deck_name):
        shutdown_event.set()


def find_template_on_screen(template_list, confidence):
    """Ищет любое изображение из списка на экране."""
    screenshot = pyautogui.screenshot(allScreens=True)
    for template in template_list:
        try:
            location = pyautogui.locate(os.path.join(TEMPLATES_DIR, template), screenshot, confidence=confidence)
            if location:
                print(f"Найдено совпадение с шаблоном: {os.path.join(TEMPLATES_DIR, template)}")
                return location
        except pyautogui.ImageNotFoundException:
            continue # Просто переходим к следующему шаблону
    return None # Если ничего не найденоwz

def main():
    pyautogui.PAUSE = 0
    # Список всех возможных шаблонов
    template_images = os.listdir(TEMPLATES_DIR)
    confidence_level = CONFIG.confidence_level

    icon_path = next(glob.iglob('icons\*.ico'), None)
    if not icon_path:
        print("Ошибка: не найден .ico файл в директории.")
        sys.exit(1)
    
    hover_text = "AnkiGaming"
    menu_options = (
        ('Edit config', icon_path, edit_config),
    )
    tray_icon = SysTrayIcon(icon_path, hover_text, menu_options, on_quit=on_quit_callback)
    tray_icon.run_in_thread()

    print("Скрипт запущен. Ожидание экрана смерти...")

    try:
        while not shutdown_event.is_set():
            #print("Проверка экрана...")
            # Ищем любой из шаблонов в списке
            location = find_template_on_screen(template_images, confidence_level)

            if location:
                on_death()
            
            if CONFIG.delay_between_screen_checks != 0:
                time.sleep(CONFIG.delay_between_screen_checks) # Пауза между проверками

    except KeyboardInterrupt:
        print("\nСкрипт остановлен пользователем.")
    except FileNotFoundError:
        # Эта ошибка теперь менее вероятна, если хотя бы один файл на месте
        print(f"Ошибка: Не найден один из файлов-шаблонов. Убедитесь, что все они в папке.")

if __name__ == "__main__":
    main()
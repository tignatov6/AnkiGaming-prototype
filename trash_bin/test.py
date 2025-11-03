import time
import sys
import glob
import threading
from TrayIcon import SysTrayIcon # Предполагается, что класс сохранен в TrayIcon.py

# --- 1. Логика вашего основного приложения ---

# Это событие будет сигналом для основного потока, что пора завершаться.
shutdown_event = threading.Event()

def main_app_function(systray_icon=None):
    """Эта функция находится в основном приложении. Мы вызовем ее из трея."""
    print("Действие из трея выполнено в основном потоке!")

def on_quit_callback(systray_icon):
    """Эта функция вызывается, когда трей готовится к выходу."""
    print('Выход из приложения...')
    shutdown_event.set() # Посылаем сигнал основному потоку на завершение

def main():
    """Главная функция вашего приложения."""
    
    # Убедитесь, что у вас есть хотя бы один .ico файл в папке
    icon_path = next(glob.iglob('*.ico'), None)
    if not icon_path:
        print("Ошибка: не найден .ico файл в директории.")
        sys.exit(1)
        
    print("Основное приложение запущено.")
    
    # --- 2. Настройка и запуск иконки в трее ---
    
    hover_text = "Мое Супер Приложение"
    menu_options = (
        ('Вызвать функцию', icon_path, main_app_function),
        # Добавьте другие пункты меню здесь
    )

    # Создаем экземпляр иконки, передавая колбэк для выхода
    tray_icon = SysTrayIcon(icon_path, hover_text, menu_options, on_quit=on_quit_callback)
    
    # Запускаем цикл обработки сообщений иконки в отдельном, неблокирующем потоке
    tray_icon.run_in_thread()
    
    # --- 3. Основной цикл вашего приложения ---
    # Ваше приложение продолжает работать здесь, не блокируясь.
    # Мы будем ждать сигнала о завершении.
    
    print("Основной цикл работает. Для выхода нажмите Quit в трее.")
    
    # Метод wait() будет блокировать этот поток до тех пор,
    # пока shutdown_event.set() не будет вызван в другом потоке.
    i = 0
    while not shutdown_event.is_set():
        print(i)
        i += 1
        time.sleep(1)
    
    print("Основное приложение завершает работу.")


if __name__ == '__main__':
    # Добавляем метод run_in_thread в класс для удобства
    def run_tray_in_thread(instance):
        thread = threading.Thread(target=instance.run, daemon=True)
        thread.start()
        return thread
    
    SysTrayIcon.run_in_thread = run_tray_in_thread
    
    main()
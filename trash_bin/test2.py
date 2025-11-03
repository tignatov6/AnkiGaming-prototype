import tkinter as tk
import pygetwindow
import pyautogui
from screeninfo import get_monitors
import threading
import time

# --- Блок 1: Независимая функция для определения монитора ---

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


# --- Блок 2: Функция для управления окном с помощью pygetwindow ---

def position_and_resize_window(window_title, target_monitor):
    """
    Находит окно по заголовку и перемещает его на целевой монитор,
    растягивая на весь экран. Работает в отдельном потоке.
    """
    # Даем главному потоку время создать окно (0.5 секунды обычно достаточно)
    time.sleep(0.5)
    
    try:
        # Ищем окно по его точному заголовку. getWindowsWithTitle возвращает список.
        win = pygetwindow.getWindowsWithTitle(window_title)[0]
        
        if win:
            print(f"Окно '{window_title}' найдено. Перемещение на монитор...")
            # Убираем возможность изменять размер и разворачивать стандартными средствами
            # Это делает его более похожим на полноэкранный режим
            win.restore() # Сначала восстанавливаем, если оно было свернуто/развернуто

            # Перемещаем окно в верхний левый угол целевого монитора
            win.moveTo(target_monitor.x, target_monitor.y)
            
            # Растягиваем окно на всю ширину и высоту целевого монитора
            win.resizeTo(target_monitor.width, target_monitor.height)
            print("Перемещение и растягивание завершено.")
        else:
            # Этот блок кода вряд ли выполнится из-за обработки исключения IndexError
            print(f"Окно с заголовком '{window_title}' не найдено.")
            
    except IndexError:
        print(f"ОШИБКА: Не удалось найти окно с заголовком '{window_title}'. Убедитесь, что заголовок точен.")
    except Exception as e:
        print(f"Произошла непредвиденная ошибка: {e}")


# --- Блок 3: Основная программа на Tkinter ---

if __name__ == "__main__":
    # 1. Задаем уникальный заголовок для нашего окна
    WINDOW_TITLE = "Мое Полноэкранное Окно v1.2.3"

    # 2. Определяем целевой монитор
    target_monitor = get_monitor_from_mouse()
    if not target_monitor:
        print("Не удалось определить монитор. Выход.")
        exit()

    # 3. Создаем простое окно Tkinter
    root = tk.Tk()
    root.title(WINDOW_TITLE)
    # Задаем начальный небольшой размер, чтобы оно просто появилось
    root.geometry("300x200") 
    root.configure(bg="black")

    # Добавляем текст
    info_label = tk.Label(
        root,
        text="Нажмите 'Escape' для выхода",
        font=("Arial", 24),
        fg="white",
        bg="black"
    )
    info_label.pack(expand=True)

    # 4. Привязываем клавишу Escape для закрытия окна
    root.bind("<Escape>", lambda event: root.destroy())

    # 5. Создаем и запускаем поток, который будет управлять окном
    # Поток-демон автоматически завершится при закрытии основной программы
    thread = threading.Thread(
        target=position_and_resize_window,
        args=(WINDOW_TITLE, target_monitor),
        daemon=True
    )
    thread.start()

    # 6. Запускаем главный цикл Tkinter. Этот вызов блокирующий.
    # Код после этой строки выполнится только после закрытия окна.
    root.mainloop()
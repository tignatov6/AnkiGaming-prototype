import os
import json
import yaml

class Localization:
    """
    Управляет загрузкой и доступом к строкам локализации из .yaml файлов.
    """
    def __init__(self, directory, fallback_lang='en'):
        """
        Инициализирует менеджер и загружает все переводы из указанной директории.

        :param directory: Путь к папке с .yaml файлами (например, 'localizations').
        :param fallback_lang: Язык, который будет использоваться, если перевод не найден.
        """
        self.fallback_lang = fallback_lang
        self.translations = {}
        self._load_from_directory(directory)

    def _load_from_directory(self, directory):
        """Сканирует директорию и загружает все .yaml файлы."""
        if not os.path.isdir(directory):
            print(f"Warning: Localization directory '{directory}' not found.")
            return

        for filename in os.listdir(directory):
            if filename.endswith('.yaml'):
                lang_code = os.path.splitext(filename)[0]
                filepath = os.path.join(directory, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        self.translations[lang_code] = yaml.safe_load(f)
                except Exception as e:
                    print(f"Error loading localization file '{filename}': {e}")
        
        if self.fallback_lang not in self.translations:
            print(f"Warning: Fallback language '{self.fallback_lang}.yaml' not found.")

    def get(self, key, lang):
        """
        Возвращает переведенную строку для указанного языка.

        Если ключ или язык не найден, пытается использовать fallback_lang.
        Если и там не найдено, возвращает сам ключ.
        """
        # Сначала ищем в желаемом языке, потом в запасном, потом возвращаем ключ
        return self.translations.get(lang, {}).get(key) or \
               self.translations.get(self.fallback_lang, {}).get(key, key)

    def get_all_as_json(self):
        """Возвращает все загруженные переводы в виде JSON-строки."""
        return json.dumps(self.translations, ensure_ascii=False)
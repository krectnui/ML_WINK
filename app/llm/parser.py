import re
import os
import json
from pathlib import Path
import tkinter
from tkinter import filedialog
from docx import Document
import pdfplumber
import chardet


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

def is_scene_header(line: str) -> bool:
    """Определяет, является ли строка заголовком сцены."""
    line = line.strip()
    if not line:
        return False

    # Приводим к единому виду
    line = re.sub(r'[–—]', '-', line)
    line = re.sub(r'\s+', ' ', line)
    
    print(f"Проверка строки: '{line}'")  # Отладочный вывод
    
    # Паттерн 1: "1. ИНТ. квартира кати. комната алёны. утро" (ваш формат)
    pattern1 = r'^\d+\.\s+(ИНТ\.|НАТ\.|ИНТЕРЬЕР|ЭКСТЕРЬЕР|INT\.|EXT\.)'
    if re.match(pattern1, line, re.IGNORECASE):
        print(f"  -> Совпадение с pattern1")
        return True
    
    # Паттерн 2: "1-1. ИНТ. КВАРТИРА - ДЕНЬ" (классический)
    pattern2 = r'^\d+-\d+\.\s+(ИНТ\.|НАТ\.|ИНТЕРЬЕР|ЭКСТЕРЬЕР|INT\.|EXT\.)'
    if re.match(pattern2, line, re.IGNORECASE):
        print(f"  -> Совпадение с pattern2") 
        return True
    
    # Паттерн 3: Просто номер сцены "1." (резервный)
    if re.match(r'^\d+\.\s*\S', line):
        print(f"  -> Совпадение с pattern3")
        return True

    # Паттерн 4: С заглавными буквами в начале "ИНТ.", "НАТ."
    if re.match(r'^(ИНТ\.|НАТ\.|ИНТЕРЬЕР|ЭКСТЕРЬЕР)', line, re.IGNORECASE):
        print(f"  -> Совпадение с pattern4")
        return True

    print(f"  -> НЕ распознан как заголовок")
    return False


def is_character_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > 50:
        return False
    
    # Разрешаем смешанный регистр (не только верхний)
    if not re.match(r'^[А-ЯЁA-Z]', stripped):
        return False
    
    # Разрешаем буквы, пробелы, тире, точки, цифры, скобки
    if not re.match(r'^[А-ЯЁA-Zа-яёa-z\s\-\.0-9\(\)]+$', stripped):
        return False
    
    words = stripped.split()
    if len(words) == 0 or len(words) > 5:
        return False
    
    # Исключаем очевидные действия (расширенный список)
    action_keywords = {
        'СМЕХ', 'ПАУЗА', 'МОЛЧАНИЕ', 'ЗВУК', 'ТИТР', 'СКЛЕЙКА', 'ПЕРЕХОД',
        'ГРАФИКА', 'ЗАЯВОЧНЫЙ', 'ОБЩИЙ', 'КРУПНО', 'ТАЙМЛАПС', 'КОНЕЦ'
    }
    if any(kw in stripped.upper() for kw in action_keywords):
        return False
    
    return True


def extract_text_from_docx(path: str) -> list:
    """Возвращает список строк из .docx."""
    doc = Document(path)
    lines = []
    for para in doc.paragraphs:
        text = para.text
        if text.strip():  # сохраняем даже пустые для структуры, но тут фильтруем
            lines.append(text)
    return lines


def extract_text_from_pdf(path: str) -> list:
    """Возвращает список строк из .pdf с указанием номера страницы."""
    lines_with_page = []
    with pdfplumber.open(path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text(x_tolerance=1, y_tolerance=1)
            if text:
                for line in text.split('\n'):
                    if line.strip():
                        lines_with_page.append((line, page_num))
    return lines_with_page


def parse_script_lines(lines_with_page: list) -> dict:
    """
    Принимает список строк (для DOCX: [str]; для PDF: [(str, page)]).
    Возвращает структурированный JSON-совместимый объект.
    """
    scenes = []
    current_scene = None
    last_character = None
    current_action_lines = []
    current_dialogue_lines = []

    # Нормализуем вход: приведём к единому формату [(line, page)]
    if lines_with_page and isinstance(lines_with_page[0], str):
        lines_with_page = [(line, None) for line in lines_with_page]

    print("=== ОТЛАДОЧНАЯ ИНФОРМАЦИЯ ===")
    print(f"Всего строк в документе: {len(lines_with_page)}")
    
    # Анализируем первые 30 строк для понимания структуры
    print("Первые 30 строк документа:")
    for i, (raw_line, page) in enumerate(lines_with_page[:30]):
        line = raw_line.strip()
        if line:  # только непустые строки
            is_header = is_scene_header(line)
            print(f"{i+1:3d}: '{line[:50]}...' -> заголовок: {is_header}")

    scene_count = 0
    for i, (raw_line, page) in enumerate(lines_with_page):
        line = raw_line.strip()
        if not line:
            continue

        # Если началась новая сцена — сохраняем предыдущую
        if is_scene_header(line):
            scene_count += 1
            print(f"НАЙДЕНА СЦЕНА {scene_count}: '{line}'")

            # Сохраняем накопленное действие или реплику перед началом сцены
            if current_action_lines:
                if current_scene:
                    current_scene["elements"].append({
                        "type": "action", 
                        "text": " ".join(current_action_lines)
                    })
                current_action_lines = []
            if current_dialogue_lines and last_character and current_scene:
                current_scene["elements"].append({
                    "type": "dialogue",
                    "character": last_character,
                    "text": " ".join(current_dialogue_lines)
                })
                current_dialogue_lines = []
                last_character = None

            # Завершаем текущую сцену
            if current_scene is not None:
                scenes.append(current_scene)

            # Начинаем новую
            current_scene = {
                "scene_id": len(scenes) + 1,
                "header": line,
                "page": page,
                "elements": []
            }
            last_character = None
            continue

        # Обработка внутри сцены
        if current_scene is None:
            # Пропускаем всё до первой сцены
            continue

        if is_character_line(line):
            # Сохраняем предыдущее действие
            if current_action_lines:
                current_scene["elements"].append({
                    "type": "action",
                    "text": " ".join(current_action_lines)
                })
                current_action_lines = []

            # Сохраняем предыдущую реплику (если была)
            if current_dialogue_lines and last_character:
                current_scene["elements"].append({
                    "type": "dialogue", 
                    "character": last_character,
                    "text": " ".join(current_dialogue_lines)
                })
                current_dialogue_lines = []

            last_character = line
        else:
            # Это либо действие, либо продолжение реплики
            if last_character is not None:
                # Продолжение реплики
                current_dialogue_lines.append(line)
            else:
                # Действие
                current_action_lines.append(line)

    # Финальная очистка после цикла
    if current_scene is not None:
        if current_action_lines:
            current_scene["elements"].append({
                "type": "action",
                "text": " ".join(current_action_lines)
            })
        if current_dialogue_lines and last_character:
            current_scene["elements"].append({
                "type": "dialogue",
                "character": last_character,
                "text": " ".join(current_dialogue_lines)
            })
        scenes.append(current_scene)

    print(f"=== РЕЗУЛЬТАТ: обработано {len(scenes)} сцен ===")
    return {"scenes": scenes}


# === ФАСАД ДЛЯ ЗАГРУЗКИ ===

def parse_script(file_path: str) -> dict:
    """Основная функция: принимает путь к .docx или .pdf → возвращает JSON."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Файл не найден: {file_path}")

    if file_path.suffix.lower() == '.docx':
        lines = extract_text_from_docx(str(file_path))
        return parse_script_lines(lines)
    elif file_path.suffix.lower() == '.pdf':
        lines_with_page = extract_text_from_pdf(str(file_path))
        return parse_script_lines(lines_with_page)
    else:
        raise ValueError("Поддерживаются только .docx и .pdf")


# === ПРИМЕР ИСПОЛЬЗОВАНИЯ ===

if __name__ == "__main__":
    import sys
    import argparse
    
    # Вариант 1: Через аргументы командной строки
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        # Вариант 2: Интерактивный ввод в консоли
        input_file = input("Введите путь к файлу сценария (.docx или .pdf): ").strip('"').strip("'")
    
    if not input_file or not os.path.exists(input_file):
        print("❌ Файл не найден или не указан")
        sys.exit(1)
    
    try:
        result = parse_script(input_file)
        output_file = Path(input_file).with_suffix('.json')
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Успешно! Результат сохранён в:\n{output_file}")
        
        # Показываем статистику
        total_scenes = len(result["scenes"])
        print(f"📊 Обработано сцен: {total_scenes}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)
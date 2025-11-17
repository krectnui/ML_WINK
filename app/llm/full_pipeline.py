# full_pipeline_fixed.py
import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List

from parser import parse_script
from main_natasha_filter import analyze_parsed_script
from predict_new import load_model_and_tokenizer
from rag_law import generate_recommendations, calculate_simple_rating  # без RuT5!

import torch

# ----------------- CONFIG -----------------
INPUT_SCRIPT = ".docx"
OUTPUT_ALL = ".json"        # Все подозрительные
OUTPUT_MAX = "max_rating_scenes.json"     # Только максимум
RUBERT_MODEL_DIR = "trained_model"
MAX_LEN = 256

def get_rating_index(rating: str) -> int:
    """Получить индекс рейтинга для сравнения"""
    rating_order = ["0+", "6+", "12+", "16+", "18+"]
    return rating_order.index(rating) if rating in rating_order else 0

def run_pipeline(input_path: str, output_all: str, output_max: str,
                 rubert_model_dir: str = RUBERT_MODEL_DIR):
    t0 = time.time()
    print("1) Парсинг сценария...")
    parsed = parse_script(input_path)
    print(f"   -> найдено сцен: {len(parsed.get('scenes', []))}")

    print("2) Первичная фильтрация (наташа)...")
    filtered = analyze_parsed_script(parsed)
    print("   -> фильтрация завершена.")

    print("3) Загружаем RuBERT модель...")
    model, tokenizer, id_to_category, level_shift = load_model_and_tokenizer(rubert_model_dir)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()
    print("   -> RuBERT загружен.")

    all_suspicious_data = []  # Для всех подозрительных сцен
    total = 0
    suspicious_total = 0

    # ПЕРВЫЙ ПРОХОД: собираем ВСЕ подозрительные сцены + рекомендации
    for scene in filtered.get("scenes", []):
        scene_id = scene.get("scene_id")
        header = scene.get("header", "")
        for element in scene.get("elements", []):
            total += 1
            text = element.get("text", "").strip()
            if not text:
                continue

            natasha = element.get("natasha_flags", {})
            is_suspicious = natasha.get("is_suspicious", False) if isinstance(natasha, dict) else False

            if not is_suspicious:
                continue

            suspicious_total += 1
            full_text = " ".join(filter(None, [element.get("character", ""), text]))

            # --- RuBERT inference ---
            inputs = tokenizer(
                full_text,
                truncation=True,
                padding="max_length",
                max_length=MAX_LEN,
                return_tensors="pt"
            )
            input_ids = inputs["input_ids"].to(device)
            attention_mask = inputs["attention_mask"].to(device)

            with torch.no_grad():
                cat_logits, lev_logits = model(input_ids=input_ids, attention_mask=attention_mask)
                cat_probs = torch.softmax(cat_logits, dim=1).cpu().numpy()[0]
                lev_probs = torch.softmax(lev_logits, dim=1).cpu().numpy()[0]

                cat_pred_id = int(cat_probs.argmax())
                lev_pred_id = int(lev_probs.argmax())

                predicted_category = "unknown"
                if isinstance(id_to_category, dict):
                    predicted_category = id_to_category.get(str(cat_pred_id)) or \
                                       id_to_category.get(cat_pred_id) or \
                                       id_to_category.get(f"cat_{cat_pred_id}", "unknown")

                predicted_level = int(lev_pred_id + int(level_shift))

            # Определяем рейтинг
            simple_rating = calculate_simple_rating(predicted_category, predicted_level)
            rating_index = get_rating_index(simple_rating)

            # Формируем category_scores
            cat_scores = {}
            for i, p in enumerate(cat_probs):
                name = id_to_category.get(str(i)) or id_to_category.get(i) or f"cat_{i}"
                cat_scores[name] = float(p)

            # Поиск оригинального элемента для типа и персонажа
            original_element = None
            for s in filtered.get("scenes", []):
                if s.get("scene_id") == scene_id:
                    for elem in s.get("elements", []):
                        if elem.get("text", "").strip() == text:
                            original_element = elem
                            break
                    if original_element:
                        break

            element_type = original_element.get("type", "action") if original_element else "action"
            character = original_element.get("character", "") if original_element else ""

            # Генерация рекомендаций
            recommendations = generate_recommendations(
                category=predicted_category,
                level=predicted_level,
                element_type=element_type,
                character=character
            )

            # Данные для записи в JSON
            scene_data = {
                "текст_сцены": text,
                "рейтинг": simple_rating,
                "индекс_рейтинга": rating_index,
                "категория": predicted_category,
                "уровень": predicted_level,
                "category_scores": cat_scores,
                "рекомендации_понижения": recommendations
            }

            all_suspicious_data.append(scene_data)

    # Если нет подозрительных — выходим
    if not all_suspicious_data:
        print("Нет подозрительных сцен для обработки")
        return

    print(f"✅ Найдено подозрительных элементов: {len(all_suspicious_data)}")

    # === ФАЙЛ 1: Все подозрительные сцены ===
    out_all = {
        "все_подозрительные_сцены": all_suspicious_data,
        "статистика": {
            "всего_элементов": total,
            "обработано_подозрительных": len(all_suspicious_data),
            "время_обработки": round(time.time() - t0, 1)
        }
    }

    with open(output_all, "w", encoding="utf-8") as f:
        json.dump(out_all, f, ensure_ascii=False, indent=2)
    print(f"💾 Сохранено ВСЕХ подозрительных: {output_all}")

    # === ФАЙЛ 2: Только сцены с МАКСИМАЛЬНЫМ рейтингом ===
    max_rating_index = max(item["индекс_рейтинга"] for item in all_suspicious_data)
    max_rating_scenes = [
        item for item in all_suspicious_data
        if item["индекс_рейтинга"] == max_rating_index
    ]

    max_rating_str = ["0+", "6+", "12+", "16+", "18+"][max_rating_index]

    out_max = {
        "обработанные_сцены": max_rating_scenes,
        "статистика": {
            "всего_подозрительных": len(all_suspicious_data),
            "сцен_с_максимальным_рейтингом": len(max_rating_scenes),
            "максимальный_рейтинг": max_rating_str,
            "время_обработки": round(time.time() - t0, 1)
        }
    }

    with open(output_max, "w", encoding="utf-8") as f:
        json.dump(out_max, f, ensure_ascii=False, indent=2)
    print(f"💾 Сохранено с МАКСИМАЛЬНЫМ рейтингом: {output_max}")

    dt = time.time() - t0
    print(f"Готово. Общее время: {dt:.1f} сек.")
    return {"result": out_max}


def process_script(
    input_path: str = INPUT_SCRIPT,
    output_all: str = OUTPUT_ALL,
    output_max: str = OUTPUT_MAX,
    rubert_model_dir: str = RUBERT_MODEL_DIR
):
    """
    Функция для запуска пайплайна с переданными параметрами.

    Args:
        input_path (str): Путь к .docx или .pdf файлу.
        output_all (str): Куда сохранить все подозрительные сцены.
        output_max (str): Куда сохранить сцены с максимальным рейтингом.
        rubert_model_dir (str): Путь к папке с моделью RuBERT.
    """
    run_pipeline(input_path, output_all, output_max, rubert_model_dir)


if __name__ == "__main__":
    process_script(
        input_path="Трек 3 - тестовый образец.docx",
        output_all="all_suspicious.json",
        output_max="max_rating_scenes.json",
        rubert_model_dir="trained_model"
    )
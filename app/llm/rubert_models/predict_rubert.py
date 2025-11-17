import os
import json
import torch
from typing import Dict, Any, List
from transformers import BertTokenizer, BertForSequenceClassification
from glob import glob


# -----------------------------
# CONFIG
# -----------------------------
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

CATEGORIES = [
    "violence",
    "profanity", 
    "erotic",
    "drugs_alcohol",
    "fear"
]

MODEL_ROOT = "models/rubert"     # у тебя модели хранятся там
INPUT_FOLDER = "example"         # где лежат входные JSON (теперь с Natasha разметкой)
OUTPUT_SUFFIX = "_rubert"        # к имени файла
MAX_LEN = 256


# -----------------------------
# LOAD MODELS
# -----------------------------
def load_all_models() -> Dict[str, Dict[str, Any]]:
    models = {}
    for cat in CATEGORIES:
        model_path = os.path.join(MODEL_ROOT, cat, "final")
        print(f"🔄 Загрузка модели {cat} из {model_path}")

        # Проверяем существование папки
        if not os.path.exists(model_path):
            print(f"❌ Папка модели не найдена: {model_path}")
            continue

        # Проверяем наличие необходимых файлов - поддерживаем оба формата
        model_files = [
            'pytorch_model.bin',  # старый формат
            'model.safetensors',  # новый формат
            'model_safetensors'   # ваш формат
        ]
        
        found_model_file = None
        for model_file in model_files:
            if os.path.exists(os.path.join(model_path, model_file)):
                found_model_file = model_file
                break
        
        if not found_model_file:
            print(f"❌ Не найден файл модели в {model_path}. Доступные файлы: {os.listdir(model_path)}")
            continue

        required_files = ['config.json', 'vocab.txt']
        missing_files = []
        for file in required_files:
            if not os.path.exists(os.path.join(model_path, file)):
                missing_files.append(file)
        
        if missing_files:
            print(f"❌ Отсутствуют файлы в {model_path}: {missing_files}")
            continue

        try:
            # Явно указываем локальную загрузку
            tokenizer = BertTokenizer.from_pretrained(model_path, local_files_only=True)
            model = BertForSequenceClassification.from_pretrained(model_path, local_files_only=True).to(DEVICE)
            model.eval()

            models[cat] = {"tokenizer": tokenizer, "model": model}
            print(f"✅ Модель {cat} успешно загружена (использован {found_model_file})")
            
        except Exception as e:
            print(f"❌ Ошибка загрузки модели {cat}: {e}")
            continue

    if not models:
        raise Exception("❌ Не удалось загрузить ни одну модель!")
        
    print(f"✅ Загружено {len(models)} моделей RuBERT.\n")
    return models


# -----------------------------
# PREDICT FOR ONE CATEGORY
# -----------------------------
def predict_category(text: str, tokenizer, model) -> Dict[str, Any]:
    tokens = tokenizer(
        text,
        padding="max_length",
        truncation=True,
        max_length=MAX_LEN,
        return_tensors="pt"
    ).to(DEVICE)

    with torch.no_grad():
        logits = model(**tokens).logits
        probs = torch.softmax(logits, dim=1).cpu().numpy()[0]

    prediction = int(probs.argmax())
    confidence = float(probs[prediction])

    return {
        "prediction": prediction,     # уровень 0–4
        "confidence": confidence      # уверенность
    }


# -----------------------------
# PROCESS ONE SCENE
# -----------------------------
def process_scene_element(text: str, models) -> Dict[str, Any]:
    result = {}

    for cat in CATEGORIES:
        if cat in models:  # только если модель загружена
            tokenizer = models[cat]["tokenizer"]
            model = models[cat]["model"]

            result[cat] = predict_category(text, tokenizer, model)
        else:
            result[cat] = {"prediction": 0, "confidence": 0.0}

    return result


# -----------------------------
# PROCESS FULL SCRIPT JSON - СОХРАНЯЕМ ТОЛЬКО ОБРАБОТАННЫЕ СЦЕНЫ
# -----------------------------
def process_script(json_data: Dict[str, Any], models) -> Dict[str, Any]:
    processed_scenes = []
    total_scenes = 0
    processed_elements = 0
    
    for scene in json_data.get("scenes", []):
        total_scenes += 1
        processed_scene_elements = []
        scene_has_processed_elements = False
        
        for element in scene.get("elements", []):
            # Проверяем, помечен ли элемент как подозрительный Natasha
            natasha_flags = element.get("natasha_flags", {})
            if natasha_flags.get("is_suspicious", False) and "text" in element:
                # Обрабатываем через RuBERT
                element["rubert_analysis"] = process_scene_element(
                    element["text"],
                    models
                )
                processed_scene_elements.append(element)
                processed_elements += 1
                scene_has_processed_elements = True
        
        # Сохраняем сцену только если в ней есть обработанные элементы
        if scene_has_processed_elements:
            processed_scene = scene.copy()
            processed_scene["elements"] = processed_scene_elements
            processed_scenes.append(processed_scene)
    
    # Создаем новый JSON только с обработанными сценами
    result = {
        "metadata": json_data.get("metadata", {}),
        "scenes": processed_scenes,
        "processing_stats": {
            "total_scenes": total_scenes,
            "processed_scenes": len(processed_scenes),
            "processed_elements": processed_elements
        }
    }
    
    print(f"📊 Обработано {len(processed_scenes)}/{total_scenes} сцен, {processed_elements} элементов")
    return result


# -----------------------------
# MAIN: PROCESS ALL FILES
# -----------------------------
def main():
    if not os.path.isdir(INPUT_FOLDER):
        print(f"❌ Папка '{INPUT_FOLDER}' не найдена.")
        return

    # Ищем файлы, обработанные Natasha (с суффиксом _natasha)
    json_files = glob(os.path.join(INPUT_FOLDER, "*_natasha.json"))
    
    # Если не нашли файлы с _natasha, ищем обычные JSON
    if not json_files:
        json_files = glob(os.path.join(INPUT_FOLDER, "*.json"))
        print("⚠️  Файлы с Natasha разметкой не найдены, используем обычные JSON")
    else:
        print("✅ Найдены файлы с Natasha разметкой")

    if not json_files:
        print(f"❌ Нет JSON-файлов в '{INPUT_FOLDER}'.")
        return

    try:
        models = load_all_models()
    except Exception as e:
        print(f"❌ Критическая ошибка загрузки моделей: {e}")
        return

    print(f"📁 Найдено {len(json_files)} JSON-файлов для обработки.\n")

    for path in json_files:
        print(f"▶ Обработка: {os.path.basename(path)}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # прогон через RuBERT (только подозрительные сцены)
            processed = process_script(data, models)

            # формирование пути для записи
            base = path.replace("_natasha", "")  # убираем суффикс natasha если есть
            base, ext = os.path.splitext(base)
            output_path = f"{base}{OUTPUT_SUFFIX}{ext}"

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(processed, f, ensure_ascii=False, indent=2)

            # Выводим статистику по файлу
            stats = processed.get("processing_stats", {})
            print(f"✅ Сохранено: {os.path.basename(output_path)}")
            print(f"   📈 Статистика: {stats['processed_scenes']} сцен, {stats['processed_elements']} элементов\n")
            
        except Exception as e:
            print(f"❌ Ошибка обработки файла {path}: {e}")
            continue

    print("🎉 Готово! Все файлы обработаны.")


# -----------------------------
# ENTRY POINT
# -----------------------------
if __name__ == "__main__":
    main()
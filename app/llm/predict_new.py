import json
import torch
import numpy as np
from transformers import AutoTokenizer
import torch.nn as nn
from torch.nn import functional as F

# --- 1. Класс модели (для загрузки) ---

class MultiTaskModel(nn.Module):
    def __init__(self, model_name, num_categories, num_levels, level_class_weights=None):
        super().__init__()
        from transformers import AutoModel
        self.bert = AutoModel.from_pretrained(model_name)
        self.dropout = nn.Dropout(0.3)
        self.category_head = nn.Linear(self.bert.config.hidden_size, num_categories)
        self.level_head = nn.Linear(self.bert.config.hidden_size, num_levels)

        # Веса не нужны для инференса, но можно сохранить для информации
        if level_class_weights is not None:
            self.level_weights = torch.tensor(level_class_weights, dtype=torch.float32)
        else:
            self.level_weights = None

    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        pooled = outputs.pooler_output
        pooled = self.dropout(pooled)
        cat_logits = self.category_head(pooled)
        lev_logits = self.level_head(pooled)
        return cat_logits, lev_logits

# --- 2. Загрузка модели и токенизатора ---

def load_model_and_tokenizer(model_path):
    # Загрузка токенизатора
    tokenizer = AutoTokenizer.from_pretrained(model_path)

    # Загрузка маппингов
    with open(f'{model_path}/category_to_id.json', 'r', encoding='utf-8') as f:
        category_to_id = json.load(f)
    id_to_category = {v: k for k, v in category_to_id.items()}

    # Загрузка весов классов (не обязательна, но можно для информации)
    weights_level = np.load(f'{model_path}/level_class_weights.npy')
    level_shift = np.load(f'{model_path}/level_shift.npy').item() # 1

    # Инициализация модели
    num_categories = len(category_to_id)  # 5
    num_levels = 4  # 0–3

    model = MultiTaskModel(
        model_name=model_path,
        num_categories=num_categories,
        num_levels=num_levels,
        level_class_weights=weights_level
    )

    # Загрузка весов
    model.load_state_dict(torch.load(f'{model_path}/pytorch_model.bin', map_location='cpu'))
    model.eval()  # Переводим в режим оценки

    return model, tokenizer, id_to_category, level_shift

# --- 3. Функция предсказания ---

def predict(input_json_path, output_json_path, model_path='trained_model', max_len=128):
    """
    Функция для фильтрации и предсказания category и level для подозрительных элементов сценария.

    Args:
        input_json_path (str): Путь к входному JSON файлу.
        output_json_path (str): Путь, куда сохранить результат.
        model_path (str): Путь к папке с обученной моделью.
        max_len (int): Максимальная длина токенизированного текста.
    """
    # Загружаем модель и токенизатор
    print("Загружаем модель и токенизатор...")
    model, tokenizer, id_to_category, level_shift = load_model_and_tokenizer(model_path)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model.to(device)
    print("Модель загружена.")

    # Загружаем JSON
    with open(input_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Подготовим список для обработанных элементов
    processed_elements = []

    # Обрабатываем сцены
    for scene in data['scenes']:
        for element in scene['elements']:
            # Проверяем, является ли элемент подозрительным
            natasha_flags = element.get('natasha_flags', {})
            is_suspicious = natasha_flags.get('is_suspicious', False)

            if is_suspicious:
                print(f"Обрабатываю подозрительный элемент: {element.get('text', '')[:50]}...")

                # Собираем текст для анализа
                text_to_analyze = element.get('text', '')
                character_text = element.get('character', '')
                full_text = f"{character_text} {text_to_analyze}".strip()

                if not full_text:
                    print("  - Текст пуст, пропускаем.")
                    continue

                # Токенизация
                inputs = tokenizer(
                    full_text,
                    truncation=True,
                    padding='max_length',
                    max_length=max_len,
                    return_tensors='pt'
                )

                input_ids = inputs['input_ids'].to(device)
                attention_mask = inputs['attention_mask'].to(device)

                # Предсказание
                with torch.no_grad():
                    cat_logits, lev_logits = model(input_ids=input_ids, attention_mask=attention_mask)

                    cat_probs = F.softmax(cat_logits, dim=1)
                    lev_probs = F.softmax(lev_logits, dim=1)

                    cat_pred_id = torch.argmax(cat_probs, dim=1).item()
                    lev_pred_id = torch.argmax(lev_probs, dim=1).item()

                    # Преобразование ID в имя категории
                    predicted_category = id_to_category.get(cat_pred_id, "unknown_category")
                    # Преобразование уровня (0–3) -> (1–4)
                    predicted_level = lev_pred_id + level_shift

                # Создаём новый элемент с минимальной информацией + результатами модели
                processed_element = {
                    "scene_id": scene['scene_id'],
                    "scene_header": scene['header'],
                    "type": element['type'],
                    "character": element.get('character', ''),
                    "text": element.get('text', ''),
                    "model_flags": {
                        "category": predicted_category,
                        "level": predicted_level,
                        "category_confidence": cat_probs[0][cat_pred_id].item(),
                        "level_confidence": lev_probs[0][lev_pred_id].item()
                    }
                }

                processed_elements.append(processed_element)
                print(f"  - Добавлено в результат: category={predicted_category}, level={predicted_level}, conf_cat={cat_probs[0][cat_pred_id].item():.3f}, conf_lev={lev_probs[0][lev_pred_id].item():.3f}")
            

    # Формируем итоговый JSON
    output_data = {
        "processed_elements": processed_elements
    }

    # Сохраняем обновлённый JSON
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Результат сохранён в {output_json_path}")

# --- 4. Пример запуска ---
if __name__ == "__main__":
    # Укажите пути к вашим файлам
    input_path = "example/Трек 3 - тестовый образец_natasha.json"        # Входной JSON
    output_path = "output_script.json"      # Выходной JSON
    model_dir = "trained_model"             # Папка с моделью

    predict(input_path, output_path, model_dir)
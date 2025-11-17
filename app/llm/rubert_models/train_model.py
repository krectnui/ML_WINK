import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset
from transformers import AutoTokenizer, AutoModel, TrainingArguments, Trainer
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score
from sklearn.utils.class_weight import compute_class_weight
import numpy as np
import os
import json

# --- 1. Подготовка данных ---

# Загрузка датасета
df = pd.read_csv('last_dataset.csv')

# Удаление строк с level = 0
print(f"До удаления level=0: {len(df)} строк")
df = df[df['level'] != 0].copy()
print(f"После удаления level=0: {len(df)} строк")

# Перенумерация level: 1,2,3,4 -> 0,1,2,3
df['level'] = df['level'] - 1
print("Уникальные значения level после перенумерации:", df['level'].unique())

# Подготовка category_to_id (начинаем с 0)
categories = df['category'].unique()
category_to_id = {cat: idx for idx, cat in enumerate(categories)}  # 0–4
id_to_category = {v: k for k, v in category_to_id.items()}

print("Новый маппинг category_to_id:", category_to_id)

df['category_id'] = df['category'].map(category_to_id)

print("Уровни (новые):", df['level'].unique())

# --- 2. Кастомный Dataset ---

class RatingDataset(Dataset):
    def __init__(self, texts, categories, levels, tokenizer, max_len=512):
        self.texts = texts
        self.categories = categories
        self.levels = levels
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = str(self.texts[idx])
        category = self.categories[idx]
        level = self.levels[idx]

        encoding = self.tokenizer(
            text,
            truncation=True,
            padding='max_length',
            max_length=self.max_len,
            return_tensors='pt'
        )

        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels_category': torch.tensor(category, dtype=torch.long),
            'labels_level': torch.tensor(level, dtype=torch.long)  # теперь 0–3
        }

# --- 3. Кастомная модель с весами классов ---

class MultiTaskModel(nn.Module):
    def __init__(self, model_name, num_categories, num_levels, level_class_weights=None):
        super().__init__()
        self.bert = AutoModel.from_pretrained(model_name)
        self.dropout = nn.Dropout(0.3)
        self.category_head = nn.Linear(self.bert.config.hidden_size, num_categories)
        self.level_head = nn.Linear(self.bert.config.hidden_size, num_levels) # теперь 4

        # Сохраняем веса для level
        if level_class_weights is not None:
            self.level_weights = torch.tensor(level_class_weights, dtype=torch.float32)
        else:
            self.level_weights = None

    def forward(self, input_ids, attention_mask, labels_category=None, labels_level=None):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        pooled = outputs.pooler_output
        pooled = self.dropout(pooled)
        cat_logits = self.category_head(pooled)
        lev_logits = self.level_head(pooled)

        loss = None
        if labels_category is not None and labels_level is not None:
            cat_loss = nn.CrossEntropyLoss()(cat_logits, labels_category)
            if self.level_weights is not None:
                lev_loss_fn = nn.CrossEntropyLoss(weight=self.level_weights.to(cat_logits.device))
            else:
                lev_loss_fn = nn.CrossEntropyLoss()
            lev_loss = lev_loss_fn(lev_logits, labels_level)
            loss = cat_loss + lev_loss

        return {
            'loss': loss,
            'logits_category': cat_logits,
            'logits_level': lev_logits
        }

# --- 4. Кастомный Trainer ---

class MultiTaskTrainer(Trainer):
    def compute_loss(self, model, inputs, return_outputs=False):
        labels_category = inputs.pop("labels_category")
        labels_level = inputs.pop("labels_level")

        outputs = model(**inputs)
        logits_category = outputs['logits_category']
        logits_level = outputs['logits_level']

        cat_loss = nn.CrossEntropyLoss()(logits_category, labels_category)
        if hasattr(model, 'level_weights') and model.level_weights is not None:
            lev_loss_fn = nn.CrossEntropyLoss(weight=model.level_weights.to(logits_category.device))
        else:
            lev_loss_fn = nn.CrossEntropyLoss()
        lev_loss = lev_loss_fn(logits_level, labels_level)
        loss = cat_loss + lev_loss

        return (loss, outputs) if return_outputs else loss

# --- 5. Основной код ---

def train_model():
    # Параметры
    model_name = 'DeepPavlov/rubert-base-cased'
    max_len = 256
    batch_size = 8
    epochs = 3
    learning_rate = 2e-5
    num_categories = len(category_to_id)  # 5 (0–4)
    num_levels = 4  # 0–3 (после удаления level=0 и перенумерации)

    print(f"num_categories: {num_categories}, num_levels: {num_levels}")

    # Вычисляем веса для level (теперь 0–3)
    level_counts = df['level'].value_counts().sort_index()
    print("Распределение level (новое):", level_counts.to_dict())
    classes_level = level_counts.index.values  # [0, 1, 2, 3]
    weights_level = compute_class_weight(
        class_weight='balanced',
        classes=classes_level,
        y=df['level'].values
    )
    weights_level = weights_level.astype(np.float32)
    print("Веса для level (новые):", weights_level)

    # Инициализация токенизатора
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    # Создание датасета
    dataset = RatingDataset(
        texts=df['text'].values,
        categories=df['category_id'].values,
        levels=df['level'].values, # теперь 0–3
        tokenizer=tokenizer,
        max_len=max_len
    )

    # Разделение на train/val
    train_size = int(0.9 * len(dataset))
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = torch.utils.data.random_split(dataset, [train_size, val_size])

    # Инициализация модели с весами
    model = MultiTaskModel(model_name, num_categories, num_levels, level_class_weights=weights_level)

    # Аргументы для Trainer
    training_args = TrainingArguments(
        output_dir='./results',
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        warmup_steps=100,
        weight_decay=0.01,
        logging_dir='./logs',
        logging_steps=10,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        report_to=None,
        save_safetensors=False,  # <-- ВАЖНО: для избежания ошибки
    )

    # Метрики
    def compute_metrics(eval_pred):
        predictions, labels = eval_pred
        # predictions: tuple (cat_logits, lev_logits)
        # labels: tuple (cat_labels, level_labels)
        cat_preds = np.argmax(predictions[0], axis=1)
        lev_preds = np.argmax(predictions[1], axis=1)
        cat_labels = labels[0]
        level_labels = labels[1]

        cat_acc = accuracy_score(cat_labels, cat_preds)
        lev_acc = accuracy_score(level_labels, lev_preds)
        cat_f1 = f1_score(cat_labels, cat_preds, average='weighted')
        lev_f1 = f1_score(level_labels, lev_preds, average='weighted')

        return {
            'category_accuracy': cat_acc,
            'level_accuracy': lev_acc,
            'category_f1': cat_f1,
            'level_f1': lev_f1,
        }

    # Инициализация Trainer
    trainer = MultiTaskTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
    )

    # Обучение
    trainer.train()

    # --- СОХРАНЕНИЕ МОДЕЛИ ---
    save_directory = 'trained_model'
    os.makedirs(save_directory, exist_ok=True)

    # Сохраняем состояние модели (веса)
    torch.save(model.state_dict(), os.path.join(save_directory, 'pytorch_model.bin'))
    # Сохраняем конфигурацию RuBERT
    model.bert.config.save_pretrained(save_directory)
    # Сохраняем токенизатор
    tokenizer.save_pretrained(save_directory)

    # Сохраняем маппинги
    with open(os.path.join(save_directory, 'category_to_id.json'), 'w', encoding='utf-8') as f:
        json.dump(category_to_id, f, ensure_ascii=False, indent=2)
    with open(os.path.join(save_directory, 'id_to_category.json'), 'w', encoding='utf-8') as f:
        json.dump(id_to_category, f, ensure_ascii=False, indent=2)
    # Сохраняем веса классов
    np.save(os.path.join(save_directory, 'level_class_weights.npy'), weights_level)
    # Сохраняем сдвиг уровня (для инференса: +1 к предсказанию, чтобы получить 1–4)
    np.save(os.path.join(save_directory, 'level_shift.npy'), np.array(1))

    print("✅ Модель обучена и сохранена в папку 'trained_model'")
    print("   Учтено: level был перенумерован с 1–4 на 0–3 для обучения.")
    print("   При инференсе к предсказанному 'level' нужно будет прибавить 1, чтобы вернуть к 1–4.")

if __name__ == "__main__":
    train_model()
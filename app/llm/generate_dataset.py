import pandas as pd
import re
import random
from collections import defaultdict

class FixedHybridCreator:
    def __init__(self):
        # Загружаем твой датасет
        try:
            self.data = pd.read_csv('labeled.csv')
            print(f"✅ Загружено {len(self.data)} примеров")
            
            # Используем колонку 'comment' для текста
            self.text_column = 'comment'
            print(f"📝 Используем колонку: '{self.text_column}'")
            
        except Exception as e:
            print(f"❌ Ошибка загрузки: {e}")
            return
        
        # ИСПРАВЛЕННЫЕ СЛОВАРИ - правильная структура с уровнями 1-4
        self.category_dicts = {
            'violence': {
                1: ['толкать', 'толчок', 'драка', 'удар', 'синяк', 'схватить', 'оттолкнуть'],
                2: ['избивать', 'кровь', 'ранить', 'перелом', 'нож', 'бить', 'побить', 'избиение'],
                3: ['убивать', 'пытка', 'расчленять', 'истязать', 'сжигать', 'стрелять', 'убийство'],
                4: ['садист', 'каннибал', 'расплавать', 'сдирать кожу', 'пытки до смерти', 'отправить на тот свет']
            },
            'profanity': {
                1: ['черт', 'блин', 'проклятье', 'боже', 'ёлки', 'чёрт'],
                2: ['дурак', 'идиот', 'кретин', 'сволочь', 'подонок', 'мудак'],
                3: ['сука', 'тварь', 'ублюдок', 'падла', 'стерва', 'мразь'],
                4: ['блять', 'хуй', 'пизда', 'ебать', 'нахуй', 'хер', 'пиздец']
            },
            'sexual': {
                1: ['целовать', 'обнимать', 'романтика', 'любовь'],
                2: ['секс', 'интим', 'постель', 'ласкать', 'страсть'],
                3: ['голый', 'обнаженный', 'половой акт', 'оргазм'],
                4: ['порно', 'изнасилование', 'порнография', 'извращение']
            },
            'substance': {
                1: ['вино', 'пиво', 'алкоголь', 'выпить', 'бокал'],
                2: ['пьяный', 'напиться', 'алкаш', 'запой', 'опьянение'],
                3: ['наркотик', 'доза', 'наркоман', 'колоться', 'кайф'],
                4: ['героин', 'кокаин', 'метадон', 'передоз', 'инъекция']
            },
            'fear': {
                1: ['страшно', 'бояться', 'испуг', 'тревога'],
                2: ['ужас', 'кошмар', 'паника', 'жуткий', 'смерть'],
                3: ['труп', 'кровь', 'призрак', 'монстр', 'убийца'],
                4: ['психоз', 'паранойя', 'сатанизм', 'ритуальное убийство']
            }
        }
    
    def auto_label_text(self, text, category_dict):
        """Автоматически размечаем текст по словарям"""
        if not isinstance(text, str):
            return 0
            
        text_lower = text.lower()
        max_level = 0
        
        for level, words in category_dict.items():
            for word in words:
                if re.search(r'\b' + re.escape(word) + r'\b', text_lower):
                    max_level = max(max_level, level)
        
        return max_level
    
    def create_hybrid_dataset(self, output_file='final_dataset_5000.csv'):
        """Создаем гибридный датасет"""
        print("🚀 Начинаем создание гибридного датасета...")
        
        all_labeled_data = []
        
        # Берем 5000 случайных примеров из твоего датасета
        sample_size = min(5000, len(self.data))
        texts = self.data[self.text_column].sample(sample_size).tolist()
        
        print(f"🔍 Обрабатываем {len(texts)} примеров...")
        
        for i, text in enumerate(texts):
            if i % 500 == 0:
                print(f"   Обработано {i}/{len(texts)}...")
            
            # Для каждого текста проверяем все категории
            for category, category_dict in self.category_dicts.items():
                level = self.auto_label_text(text, category_dict)
                if level > 0:  # сохраняем только с нарушениями
                    all_labeled_data.append({
                        'category': category,
                        'text': text,
                        'level': level,
                        'source': 'auto'
                    })
        
        # Сохраняем автоматически размеченные данные
        auto_df = pd.DataFrame(all_labeled_data)
        
        print(f"✅ Автоматически размечено: {len(auto_df)} примеров")
        
        if len(auto_df) == 0:
            print("❌ Не найдено подходящих примеров для разметки!")
            return
        
        # Выбираем 50 случайных для ручной проверки (вместо 100 для скорости)
        manual_check_samples = auto_df.sample(min(50, len(auto_df)))
        
        print(f"\n🎯 РУЧНАЯ ПРОВЕРКА {len(manual_check_samples)} ПРИМЕРОВ")
        print("=" * 50)
        
        corrections = []
        for i, (idx, row) in enumerate(manual_check_samples.iterrows()):
            print(f"\n--- Пример {i+1}/{len(manual_check_samples)} ---")
            print(f"Категория: {row['category']}")
            print(f"Текст: {row['text']}")
            print(f"Авторазметка: Уровень {row['level']}")
            
            correct_level = input("Исправить уровень (0-4, Enter - оставить): ")
            if correct_level.strip() and correct_level.isdigit():
                correct_level = int(correct_level)
                if 0 <= correct_level <= 4:
                    corrections.append((idx, correct_level))
            print("-" * 40)
        
        # Применяем исправления
        for idx, new_level in corrections:
            auto_df.loc[idx, 'level'] = new_level
            auto_df.loc[idx, 'source'] = 'manual_corrected'
        
        print(f"✅ Исправлено {len(corrections)} примеров")
        
        # Финальное сохранение
        auto_df.to_csv(output_file, index=False)
        
        # Статистика
        print(f"\n🎉 ФИНАЛЬНЫЙ ДАТАСЕТ СОХРАНЕН: {output_file}")
        print("=" * 50)
        print(f"📊 Общий размер: {len(auto_df)} примеров")
        
        print(f"\n📈 РАСПРЕДЕЛЕНИЕ ПО КАТЕГОРИЯМ:")
        for category in auto_df['category'].unique():
            count = len(auto_df[auto_df['category'] == category])
            print(f"   - {category}: {count} примеров")
            
            # Распределение по уровням внутри категории
            for level in range(1, 5):
                level_count = len(auto_df[(auto_df['category'] == category) & (auto_df['level'] == level)])
                if level_count > 0:
                    print(f"     Уровень {level}: {level_count}")
        
        print(f"\n📝 ИСТОЧНИКИ РАЗМЕТКИ:")
        source_stats = auto_df['source'].value_counts()
        for source, count in source_stats.items():
            print(f"   - {source}: {count} примеров")
        
        return auto_df

# ЗАПУСК
if __name__ == "__main__":
    print("🎯 ЗАПУСК СОЗДАНИЯ ГИБРИДНОГО ДАТАСЕТА")
    print("=" * 60)
    
    creator = FixedHybridCreator()
    final_dataset = creator.create_hybrid_dataset()
    
    print("\n✅ ПРОЦЕСС ЗАВЕРШЕН!")
    print("Теперь у тебя есть готовый датасет для обучения моделей!")
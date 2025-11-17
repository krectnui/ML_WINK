from gensim.models import KeyedVectors
from ruwordnet import RuWordNet
import json
import os

MODEL_PATH = "models/ruscorpora_upos_skipgram_300_5_2018.vec"
BASE_PATH = "lexicons/base_lexicons.json"
EXPANDED_PATH = "lexicons/expanded_lexicons.json"
RUWORDNET_PATH = "models/ruwordnet.db"

SIM_THRESHOLD = 0.45
MAX_NEW_WORDS = 15


def load_model():
    """Загружает Word2Vec и RuWordNet."""
    print("🔁 Загружаем Word2Vec и RuWordNet...")
    model = KeyedVectors.load_word2vec_format(MODEL_PATH, binary=False)
    wn = RuWordNet(RUWORDNET_PATH)
    print("✅ Модели загружены.")
    return model, wn


def expand_word_set(base_words, model, wn):
    """Расширяет базовый набор слов синонимами и похожими словами."""
    expanded = set(base_words)
    for w in base_words:
        # Расширение через Word2Vec
        if model and w in model:
            for sim, score in model.most_similar(w, topn=MAX_NEW_WORDS):
                if score >= SIM_THRESHOLD:
                    expanded.add(sim)
        # Расширение через RuWordNet
        if wn:
            for sense in wn.get_senses(w):
                synset = sense.synset
                for synonym in synset.senses:
                    expanded.add(synonym.name)
    return list(expanded)


def expand_all_lexicons():
    """Расширяет все словари из base_lexicons.json и сохраняет в expanded_lexicons.json."""
    model, wn = load_model()

    with open(BASE_PATH, "r", encoding="utf-8") as f:
        base = json.load(f)

    expanded = {}
    for category, parts in base.items():
        expanded[category] = {}
        for key, words in parts.items():
            if not isinstance(words, list):
                continue
            expanded[category][key] = expand_word_set(words, model, wn)

    os.makedirs(os.path.dirname(EXPANDED_PATH), exist_ok=True)
    with open(EXPANDED_PATH, "w", encoding="utf-8") as f:
        json.dump(expanded, f, ensure_ascii=False, indent=2)

    print(f"✅ Расширенные словари сохранены в {EXPANDED_PATH}")


def load_expanded_lexicons():
    """Подгружает готовые словари."""
    if not os.path.exists(EXPANDED_PATH):
        print("⚠️ expanded_lexicons.json не найден. Запусти expand_all_lexicons() один раз.")
        return {}
    with open(EXPANDED_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

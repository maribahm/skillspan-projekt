"""
Laden der vorbereiteten Daten + Ausrichtung der Wort-Labels auf Subword-Tokens.

Problem: Der Datensatz hat ein Label pro WORT, BERT arbeitet aber mit SUBWORDS.
  "cloud-based"  ->  ["cloud", "-", "based"]   (3 Subwords, aber nur 1 Label)

Zwei Strategien (-> Ablation "first vs. all"):
  "first": nur das erste Subword bekommt das Label, alle weiteren -100
           (-100 wird von CrossEntropyLoss ignoriert)
  "all":   alle Subwords bekommen ein Label; aus B wird bei Folge-Subwords I

Hinweis: Fuer Mean-Pooling ueber Subwords (statt "first") liefert encode() zusaetzlich
`word_ids`, damit das Modell die Subwords eines Wortes zusammenfassen kann.
"""
import json
from pathlib import Path

IGNORE = -100


def load_split(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_labels(path="data/processed/labels.json"):
    """Gibt fuer jede Ebene (skill, knowledge) label2id und id2label zurueck."""
    labels = json.loads(Path(path).read_text(encoding="utf-8"))
    return {
        layer: {"label2id": {l: i for i, l in enumerate(ls)}, "id2label": dict(enumerate(ls))}
        for layer, ls in labels.items()
    }


def align_labels(word_ids, word_labels, label2id, strategy="first"):
    """word_ids: fuer jedes Subword der Index des zugehoerigen Wortes (None = [CLS]/[SEP]/Padding)."""
    aligned, prev = [], None
    for wid in word_ids:
        if wid is None:                       # Spezialtoken
            aligned.append(IGNORE)
        elif wid != prev:                     # erstes Subword eines Wortes
            aligned.append(label2id[word_labels[wid]])
        elif strategy == "all":               # Folge-Subword
            tag = word_labels[wid]
            if tag.startswith("B-"):
                tag = "I-" + tag[2:]
            aligned.append(label2id[tag])
        else:
            aligned.append(IGNORE)
        prev = wid
    return aligned


def encode(example, tokenizer, labels, strategy="first", max_length=512):
    """Tokenisiert einen Satz und erzeugt Labels fuer beide Ebenen.

    tokenizer: ein *Fast*-Tokenizer von Hugging Face (noetig fuer word_ids()).
               Bei RoBERTa-Modellen mit add_prefix_space=True laden.
    """
    enc = tokenizer(example["tokens"], is_split_into_words=True,
                    truncation=True, max_length=max_length)
    word_ids = enc.word_ids()
    enc["labels_skill"] = align_labels(word_ids, example["skill_tags"],
                                       labels["skill"]["label2id"], strategy)
    enc["labels_knowledge"] = align_labels(word_ids, example["knowledge_tags"],
                                           labels["knowledge"]["label2id"], strategy)
    enc["word_ids"] = [-1 if w is None else w for w in word_ids]
    # Kontrolle: Woerter ohne ein einziges Subword. Ursache ist entweder Truncation
    # oder ein Token aus reinen Steuerzeichen (im Datensatz z. B. '\x95', '\x1a', '\u200d'),
    # das der Tokenizer komplett entfernt. Solche Woerter bekommen spaeter 'O'.
    covered = {w for w in word_ids if w is not None}
    enc["n_words_without_subwords"] = len(example["tokens"]) - len(covered)
    enc["was_truncated"] = len(enc["input_ids"]) >= max_length
    return enc


def to_word_level(pred_ids, word_ids, n_words, id2label):
    """Subword-Vorhersagen -> ein Tag pro Wort (Vorhersage des ersten Subwords).
    Woerter, die durch Truncation fehlen, bekommen 'O'. Ergebnis ist direkt fuer seqeval nutzbar."""
    tags, prev = ["O"] * n_words, None
    for p, wid in zip(pred_ids, word_ids):
        if wid is not None and wid != -1 and wid != prev:
            tags[wid] = id2label[int(p)]
        prev = wid
    return tags

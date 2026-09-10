"""
Bereitet den SkillSpan-Datensatz fuer das Training vor.

Schritte:
  1. Rohdaten laden (data/raw/{train,dev,test}.json, JSON Lines)
  2. Konsistenz pruefen (gleiche Laenge von Tokens und Tags, gueltige BIO-Tags)
  3. Ungueltige BIO-Folgen reparieren (I direkt nach O wird zu B)
  4. Tags typisieren: B/I/O  ->  B-SKILL / I-SKILL / O  bzw.  B-KNOWLEDGE / ...
  5. Nur Train: ueberlange Saetze in Stuecke teilen, ohne einen Span zu zerschneiden
  6. Dev/Test: markieren, ob der Satz identisch auch im Train-Set vorkommt
  7. Ergebnis nach data/processed/ schreiben + labels.json + stats.json

Dev und Test werden inhaltlich NICHT veraendert (ausser Schritt 3),
damit die Evaluation mit dem Paper vergleichbar bleibt.

Aufruf:  python scripts/prepare_data.py --raw data/raw --out data/processed --max-words 100
"""
import argparse
import json
from collections import Counter
from pathlib import Path

# Rohdaten-Feld -> (neues Feld, Entitaetstyp)
LAYERS = {"tags_skill": ("skill_tags", "SKILL"), "tags_knowledge": ("knowledge_tags", "KNOWLEDGE")}
SPLITS = ["train", "dev", "test"]


def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def repair_bio(tags):
    """I direkt nach O (oder am Satzanfang) ist ungueltig -> wird zu B.
    Gibt (reparierte_tags, anzahl_reparaturen) zurueck."""
    fixed, n, prev = [], 0, "O"
    for t in tags:
        if t == "I" and prev == "O":
            t, n = "B", n + 1
        fixed.append(t)
        prev = t
    return fixed, n


def add_type(tags, typ):
    return [t if t == "O" else f"{t}-{typ}" for t in tags]


def has_span(example):
    return any(t != "O" for t in example["skill_tags"] + example["knowledge_tags"])


def split_long(example, max_words):
    """Teilt einen Satz in Stuecke <= max_words.
    Geschnitten wird nur vor einem Token, das in KEINER Label-Ebene ein I-Tag hat,
    damit kein Span zerteilt wird."""
    n = len(example["tokens"])
    if n <= max_words:
        return [example]
    chunks, start = [], 0
    while start < n:
        end = min(start + max_words, n)
        if end < n:
            cut = end
            while cut > start and (example["skill_tags"][cut].startswith("I-")
                                   or example["knowledge_tags"][cut].startswith("I-")):
                cut -= 1
            if cut > start:  # sonst: Span laenger als max_words -> hart schneiden
                end = cut
        chunk = {k: (v[start:end] if isinstance(v, list) else v) for k, v in example.items()}
        chunk["id"] = f"{example['id']}_c{len(chunks)}"
        chunks.append(chunk)
        start = end
    return chunks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="data/raw")
    ap.add_argument("--out", default="data/processed")
    ap.add_argument("--max-words", type=int, default=100,
                    help="Max. Woerter pro Trainingssatz (BERT verarbeitet max. 512 Subwords)")
    args = ap.parse_args()
    raw, out = Path(args.raw), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    data, stats = {}, {}
    for split in SPLITS:
        rows, repairs, processed = load_jsonl(raw / f"{split}.json"), 0, []
        for i, r in enumerate(rows):
            assert len(r["tokens"]) == len(r["tags_skill"]) == len(r["tags_knowledge"]), \
                f"{split} Zeile {i}: Laengen von Tokens und Tags ungleich"
            ex = {"id": f"{split}_{i}", "doc_idx": r["idx"], "source": r["source"], "tokens": r["tokens"]}
            for raw_key, (new_key, typ) in LAYERS.items():
                assert set(r[raw_key]) <= {"B", "I", "O"}, f"{split} Zeile {i}: unbekannter Tag"
                tags, n = repair_bio(r[raw_key])
                repairs += n
                ex[new_key] = add_type(tags, typ)
            processed.append(ex)
        data[split] = processed
        stats[split] = {"saetze_roh": len(rows), "bio_reparaturen": repairs}

    # Nur Train: lange Saetze teilen (Dev/Test bleiben unveraendert)
    stats["train"]["geteilte_lange_saetze"] = sum(len(e["tokens"]) > args.max_words for e in data["train"])
    data["train"] = [c for e in data["train"] for c in split_long(e, args.max_words)]

    # Dev/Test: identische Saetze im Train-Set markieren (Boilerplate wie "Job description:")
    train_keys = {tuple(r["tokens"]) for r in load_jsonl(raw / "train.json")}
    for split in ["dev", "test"]:
        for e in data[split]:
            e["seen_in_train"] = tuple(e["tokens"]) in train_keys

    for split in SPLITS:
        rows, s = data[split], stats[split]
        s["saetze_verarbeitet"] = len(rows)
        s["skill_spans"] = sum(t.startswith("B-") for e in rows for t in e["skill_tags"])
        s["knowledge_spans"] = sum(t.startswith("B-") for e in rows for t in e["knowledge_tags"])
        s["saetze_ohne_span"] = sum(not has_span(e) for e in rows)
        s["quellen"] = dict(Counter(e["source"] for e in rows))
        s["max_woerter_pro_satz"] = max(len(e["tokens"]) for e in rows)
        if split != "train":
            s["identisch_mit_train"] = sum(e["seen_in_train"] for e in rows)
            s["identisch_mit_train_mit_span"] = sum(e["seen_in_train"] and has_span(e) for e in rows)
        with open(out / f"{split}.jsonl", "w", encoding="utf-8") as f:
            for e in rows:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")

    labels = {"skill": ["O", "B-SKILL", "I-SKILL"], "knowledge": ["O", "B-KNOWLEDGE", "I-KNOWLEDGE"]}
    (out / "labels.json").write_text(json.dumps(labels, indent=2), encoding="utf-8")
    (out / "stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

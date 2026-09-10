"""
Sanity-Check: Funktioniert das Subword-Alignment mit einem echten Tokenizer?

Kodiert jeden Satz, rechnet die Gold-Labels zurueck auf Wort-Ebene und prueft mit
seqeval, dass F1 = 1.0 herauskommt. Ist das nicht so, ist das Alignment kaputt.
Gibt ausserdem aus, wie lang die Saetze in Subwords werden (wichtig fuer max_length).

Aufruf (einmal pro Modell, das ihr verwenden wollt):
  python scripts/check_alignment.py --model bert-base-cased
  python scripts/check_alignment.py --model jjzha/jobbert-base-cased   # exakten Namen auf huggingface.co/jjzha pruefen
  python scripts/check_alignment.py --model xlm-roberta-base
"""
import argparse
import sys
from pathlib import Path

from seqeval.metrics import f1_score
from transformers import AutoTokenizer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from data import encode, load_labels, load_split, to_word_level  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="bert-base-cased")
    ap.add_argument("--data", default="data/processed")
    ap.add_argument("--max-length", type=int, default=512)
    args = ap.parse_args()

    extra = {"add_prefix_space": True} if "roberta" in args.model and "xlm" not in args.model else {}
    tok = AutoTokenizer.from_pretrained(args.model, use_fast=True, **extra)
    labels = load_labels(Path(args.data) / "labels.json")
    all_ok = True

    for split in ["train", "dev", "test"]:
        rows = load_split(Path(args.data) / f"{split}.jsonl")
        for strategy in ["first", "all"]:
            for layer in ["skill", "knowledge"]:
                gold, rec, lengths, truncated, no_sub = [], [], [], 0, 0
                for ex in rows:
                    enc = encode(ex, tok, labels, strategy, args.max_length)
                    word_ids = [None if w == -1 else w for w in enc["word_ids"]]
                    ids = [0 if x == -100 else x for x in enc[f"labels_{layer}"]]
                    rec.append(to_word_level(ids, word_ids, len(ex["tokens"]), labels[layer]["id2label"]))
                    gold.append(ex[f"{layer}_tags"])
                    lengths.append(len(enc["input_ids"]))
                    truncated += enc["was_truncated"]
                    no_sub += enc["n_words_without_subwords"]
                f1 = f1_score(gold, rec)
                all_ok &= f1 == 1.0
                print(f"{split:5} {strategy:5} {layer:9} F1={f1:.4f}  max_subwords={max(lengths)}  "
                      f"gekuerzte_saetze={truncated}  woerter_ohne_subword={no_sub}")

    print("\nAlignment OK" if all_ok else "\nFEHLER im Alignment - F1 muss 1.0 sein!")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lockerer_f1.py -- diagnostische Metriken neben dem strikten Span-F1.

  strikt   Span zaehlt nur bei exakt gleichen Grenzen (entspricht seqeval)
  locker   Span zaehlt, sobald er einen Gold-Span ueberlappt
  Token    Bewertung auf Token-Ebene (alle Tokens innerhalb eines Spans)

Der strikte F1 bleibt die Hauptmetrik. Die lockere Variante trennt die Frage
"wird der Skill ueberhaupt gefunden?" von der Frage "stimmen die Grenzen?".

Hinweis zur Interpretation: Die lockere Metrik beguenstigt lange Spans, weil ein
langer Gold-Span leichter von irgendeiner Vorhersage ueberlappt wird. Vergleiche
zwischen Testsets mit unterschiedlicher mittlerer Spanlaenge sind deshalb mit
Vorsicht zu lesen.

Aufruf:
  python3 scripts/lockerer_f1.py results/predictions/*.jsonl --layer skill
"""

import argparse
import json
import os


def spans(tags):
    out, i = [], 0
    while i < len(tags):
        if tags[i] != "O":
            j = i + 1
            while j < len(tags) and tags[j].startswith("I-"):
                j += 1
            out.append((i, j))
            i = j
        else:
            i += 1
    return out


def f1(p, r):
    return 2 * p * r / (p + r) if p + r else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dateien", nargs="+")
    ap.add_argument("--layer", default="skill")
    args = ap.parse_args()
    L = args.layer

    print(f"{'Datei':38s} {'strikt':>8s} {'locker':>8s} {'Token':>8s}   "
          f"{'lock. P':>8s} {'lock. R':>8s}  Ø Gold-Span")
    for path in args.dateien:
        rows = [json.loads(l) for l in open(path, encoding="utf-8")]
        tp = lp = lr = n_gold = n_pred = 0
        tok_tp = tok_g = tok_p = 0
        gold_len = 0
        for r in rows:
            G, P = spans(r[f"gold_{L}"]), spans(r[f"pred_{L}"])
            n_gold += len(G)
            n_pred += len(P)
            gold_len += sum(b - a for a, b in G)
            tp += len(set(G) & set(P))
            ov = lambda a, b: a[0] < b[1] and b[0] < a[1]
            lp += sum(any(ov(p, g) for g in G) for p in P)
            lr += sum(any(ov(p, g) for p in P) for g in G)
            gt = {i for a, b in G for i in range(a, b)}
            pt = {i for a, b in P for i in range(a, b)}
            tok_tp += len(gt & pt)
            tok_g += len(gt)
            tok_p += len(pt)
        s = f1(tp / n_pred, tp / n_gold)
        l = f1(lp / n_pred, lr / n_gold)
        t = f1(tok_tp / tok_p, tok_tp / tok_g)
        print(f"{os.path.basename(path):38s} {s:8.4f} {l:8.4f} {t:8.4f}   "
              f"{lp/n_pred:8.3f} {lr/n_gold:8.3f}  {gold_len/n_gold:6.2f} Tokens")


if __name__ == "__main__":
    main()

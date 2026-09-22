#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fehleranalyse.py -- ordnet jeden Vorhersagefehler auf Span-Ebene einer Kategorie zu.

Eingabe: jsonl aus results/predictions/ (tokens, gold_<layer>, pred_<layer>)

Kategorien (aus Sicht der Gold-Spans, ausser "falscher Alarm"):
  korrekt         exakt gleiche Grenzen
  zu lang         Vorhersage enthaelt den Gold-Span und mehr
  zu kurz         Vorhersage liegt innerhalb des Gold-Spans
  verschoben      ueberlappt, aber keiner enthaelt den anderen
  zersplittert    ein Gold-Span wird von mehreren Vorhersagen getroffen
  uebersehen      keine Vorhersage ueberlappt den Gold-Span
  falscher Alarm  Vorhersage ueberlappt keinen Gold-Span (Sicht der Vorhersagen)

Ausgabe:
  Zusammenfassung auf der Konsole
  <out>_beispiele.tsv   Stichprobe je Kategorie zum Durchsehen von Hand

Aufruf:
  python3 scripts/fehleranalyse.py results/predictions/<datei>.jsonl --layer skill --out results/fehler_en
"""

import argparse
import json
import random
from collections import Counter, defaultdict


def spans(tags):
    out, i = [], 0
    while i < len(tags):
        if tags[i].startswith("B-"):
            j = i + 1
            while j < len(tags) and tags[j].startswith("I-"):
                j += 1
            out.append((i, j))
            i = j
        elif tags[i].startswith("I-"):          # tolerant gegenueber ungueltigem I am Anfang
            j = i + 1
            while j < len(tags) and tags[j].startswith("I-"):
                j += 1
            out.append((i, j))
            i = j
        else:
            i += 1
    return out


def ov(a, b):
    return a[0] < b[1] and b[0] < a[1]


def bucket(n):
    return "1" if n == 1 else "2-3" if n <= 3 else "4-6" if n <= 6 else "7+"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pred")
    ap.add_argument("--layer", default="skill")
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=30, help="Beispiele pro Kategorie")
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(args.pred, encoding="utf-8")]
    L = args.layer
    cat_gold = Counter()
    n_gold = n_pred = n_fa = 0
    by_len = defaultdict(Counter)
    extra_left, extra_right, miss_left, miss_right = Counter(), Counter(), Counter(), Counter()
    first_tok_missed = Counter()
    examples = defaultdict(list)

    for r in rows:
        toks = r["tokens"]
        G = spans(r[f"gold_{L}"])
        P = spans(r[f"pred_{L}"])
        n_gold += len(G)
        n_pred += len(P)
        sent = " ".join(toks)
        txt = lambda s: " ".join(toks[s[0]:s[1]])

        for g in G:
            hits = [p for p in P if ov(p, g)]
            if g in P:
                c = "korrekt"
            elif not hits:
                c = "uebersehen"
                first_tok_missed[toks[g[0]].lower()] += 1
            elif len(hits) > 1:
                c = "zersplittert"
            else:
                p = hits[0]
                if p[0] <= g[0] and p[1] >= g[1]:
                    c = "zu lang"
                    for t in toks[p[0]:g[0]]:
                        extra_left[t.lower()] += 1
                    for t in toks[g[1]:p[1]]:
                        extra_right[t.lower()] += 1
                elif p[0] >= g[0] and p[1] <= g[1]:
                    c = "zu kurz"
                    for t in toks[g[0]:p[0]]:
                        miss_left[t.lower()] += 1
                    for t in toks[p[1]:g[1]]:
                        miss_right[t.lower()] += 1
                else:
                    c = "verschoben"
            cat_gold[c] += 1
            by_len[bucket(g[1] - g[0])][c] += 1
            if c != "korrekt":
                examples[c].append((r["id"], txt(g), " | ".join(txt(p) for p in hits), sent))

        for p in P:
            if not any(ov(p, g) for g in G):
                n_fa += 1
                examples["falscher Alarm"].append((r["id"], "", txt(p), sent))

    tp = cat_gold["korrekt"]
    prec = tp / n_pred if n_pred else 0
    rec = tp / n_gold if n_gold else 0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0

    print(f"Datei: {args.pred}")
    print(f"Saetze {len(rows)}  Gold-Spans {n_gold}  Vorhergesagte Spans {n_pred}")
    print(f"P {prec:.4f}  R {rec:.4f}  F1 {f1:.4f}   (Kontrolle gegen seqeval)\n")

    print("Gold-Spans nach Kategorie")
    for c in ["korrekt", "zu lang", "zu kurz", "verschoben", "zersplittert", "uebersehen"]:
        print(f"  {c:14s} {cat_gold[c]:5d}  ({100*cat_gold[c]/n_gold:5.1f} %)")
    grenz = cat_gold["zu lang"] + cat_gold["zu kurz"] + cat_gold["verschoben"] + cat_gold["zersplittert"]
    print(f"  {'-> Grenzfehler gesamt':22s} {grenz:5d}  ({100*grenz/n_gold:5.1f} % der Gold-Spans)")
    print(f"Falsche Alarme (Vorhersagen ohne Ueberlappung): {n_fa}  "
          f"({100*n_fa/n_pred:.1f} % der Vorhersagen)\n")

    print("Trefferquote (Recall) nach Laenge des Gold-Spans")
    for b in ["1", "2-3", "4-6", "7+"]:
        n = sum(by_len[b].values())
        if n:
            print(f"  {b:4s} Tokens  n={n:4d}  exakt {100*by_len[b]['korrekt']/n:5.1f} %"
                  f"   uebersehen {100*by_len[b]['uebersehen']/n:5.1f} %"
                  f"   Grenzfehler {100*(n-by_len[b]['korrekt']-by_len[b]['uebersehen'])/n:5.1f} %")

    def top(c, k=10):
        return ", ".join(f"{w} ({n})" for w, n in c.most_common(k)) or "-"
    print("\nZu lang -- zusaetzliche Tokens links: ", top(extra_left))
    print("Zu lang -- zusaetzliche Tokens rechts:", top(extra_right))
    print("Zu kurz -- fehlende Tokens links:     ", top(miss_left))
    print("Zu kurz -- fehlende Tokens rechts:    ", top(miss_right))
    print("Uebersehen -- haeufigste erste Tokens:", top(first_tok_missed, 15))

    rnd = random.Random(0)
    with open(f"{args.out}_beispiele.tsv", "w", encoding="utf-8") as f:
        f.write("kategorie\tid\tgold_span\tvorhersage\tsatz\tnotiz\n")
        for c in ["uebersehen", "falscher Alarm", "zu kurz", "zu lang", "verschoben", "zersplittert"]:
            ex = examples[c][:]
            rnd.shuffle(ex)
            for e in ex[:args.n]:
                f.write("\t".join([c, *e, ""]) + "\n")
    print(f"\nStichprobe geschrieben: {args.out}_beispiele.tsv")


if __name__ == "__main__":
    main()

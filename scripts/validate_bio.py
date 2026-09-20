#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_bio.py (v2) -- prueft CoNLL-Dateien auf Format- und BIO-Fehler.
Kommt mit 2 Spalten (Token + ein Layer) und 3 Spalten (Token + SKILL + KNOWLEDGE) klar;
die Spaltenzahl wird aus der ersten Datenzeile der Datei bestimmt und muss konstant bleiben.

Geprueft wird je Label-Spalte:
  F1  konstante Spaltenzahl in der ganzen Datei
  F2  Token nicht leer, kein Whitespace im Token
  F3  Label im erlaubten Set {O, B-SKILL, I-SKILL, B-KNOWLEDGE, I-KNOWLEDGE}
  B1  kein I-X am Satzanfang
  B2  kein I-X nach O
  B3  kein I-X nach einem Label einer anderen Klasse
  S1  Datei enthaelt Tokens
  S2  Datei endet mit Leerzeile

Exit-Code 0 = gueltig, 1 = Fehler.

Aufruf:
    python3 validate_bio.py datei.conll [...]
    python3 validate_bio.py --dir conll_skill/
"""

import argparse
import os
import sys
from collections import Counter

ENTITIES = ("SKILL", "KNOWLEDGE")
ALLOWED = {"O"} | {f"{p}-{e}" for e in ENTITIES for p in ("B", "I")}


def entity_of(label):
    return label.split("-", 1)[1] if label != "O" else None


def validate_file(path):
    errors, stats = [], Counter()
    lengths = Counter()

    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")

    ncols = None
    prev = []          # Labels des Vorgaengertokens je Spalte
    open_len = []      # offene Spanlaenge je Spalte
    sent_tokens = 0
    sent_id = "(ohne sent_id)"

    def close_sentence():
        nonlocal sent_tokens, prev, open_len
        if sent_tokens > 0:
            stats["sentences"] += 1
            for c, l in enumerate(open_len):
                if l:
                    lengths[(c, l)] += 1
        sent_tokens = 0
        prev = ["O"] * (ncols - 1 if ncols else 0)
        open_len = [0] * (ncols - 1 if ncols else 0)

    for lineno, raw in enumerate(lines, start=1):
        line = raw.rstrip("\r")
        if line.startswith("#"):
            if line.startswith("# sent_id"):
                sent_id = line.split("=", 1)[1].strip()
            continue
        if line == "":
            close_sentence()
            continue

        cols = line.split("\t")
        if ncols is None:
            ncols = len(cols)
            if ncols < 2:
                errors.append(f"{path}:{lineno} [F1] mindestens 2 Spalten erwartet: {line!r}")
                ncols = None
                continue
            prev = ["O"] * (ncols - 1)
            open_len = [0] * (ncols - 1)
        if len(cols) != ncols:
            errors.append(f"{path}:{lineno} [F1] {len(cols)} Spalten, erwartet {ncols}: {line!r}")
            continue

        token, labels = cols[0], cols[1:]
        if token == "" or any(c.isspace() for c in token):
            errors.append(f"{path}:{lineno} [F2] ungueltiges Token: {token!r}")

        for c, label in enumerate(labels):
            if label not in ALLOWED:
                errors.append(f"{path}:{lineno} [F3] Spalte {c+2}: unbekanntes Label {label!r}")
                prev[c] = "O"
                open_len[c] = 0
                continue
            if label.startswith("I-"):
                ent = entity_of(label)
                if sent_tokens == 0:
                    errors.append(f"{path}:{lineno} [B1] Spalte {c+2}: I-{ent} am Satzanfang "
                                  f"(sent_id={sent_id}): {token!r}")
                elif prev[c] == "O":
                    errors.append(f"{path}:{lineno} [B2] Spalte {c+2}: I-{ent} ohne B-{ent} "
                                  f"(sent_id={sent_id}): {token!r}")
                elif entity_of(prev[c]) != ent:
                    errors.append(f"{path}:{lineno} [B3] Spalte {c+2}: I-{ent} nach {prev[c]} "
                                  f"(sent_id={sent_id}): {token!r}")
                else:
                    open_len[c] += 1
            elif label.startswith("B-"):
                if open_len[c]:
                    lengths[(c, open_len[c])] += 1
                open_len[c] = 1
                stats[f"spans_{c}"] += 1
            else:
                if open_len[c]:
                    lengths[(c, open_len[c])] += 1
                open_len[c] = 0
            stats[label] += 1
            prev[c] = label

        stats["tokens"] += 1
        sent_tokens += 1

    if sent_tokens > 0:
        close_sentence()
        errors.append(f"{path} [S2] Datei endet nicht mit Leerzeile")
    if stats["tokens"] == 0:
        errors.append(f"{path} [S1] keine Tokens gefunden")

    return errors, stats, ncols or 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--dir")
    args = ap.parse_args()

    paths = list(args.files)
    if args.dir:
        paths += [os.path.join(args.dir, fn) for fn in sorted(os.listdir(args.dir))
                  if fn.endswith(".conll")]
    if not paths:
        ap.error("keine Dateien angegeben")

    all_errors, total = [], Counter()
    for path in paths:
        errors, stats, ncols = validate_file(path)
        all_errors += errors
        total.update(stats)
        status = "OK " if not errors else f"{len(errors)} FEHLER"
        spans = sum(v for k, v in stats.items() if k.startswith("spans_"))
        print(f"[{status}] {path}: {ncols} Spalten, {stats['sentences']} Saetze, "
              f"{stats['tokens']} Tokens, {spans} Spans")

    print("\n--- Gesamt ---")
    print(f"Dateien: {len(paths)}   Saetze: {total['sentences']}   Tokens: {total['tokens']}")
    for ent in ENTITIES:
        b, i = total[f"B-{ent}"], total[f"I-{ent}"]
        if b or i:
            print(f"{ent:10s} B: {b:4d}   I: {i:4d}   Span-Tokens: {b+i:4d} "
                  f"({100.0*(b+i)/total['tokens']:.1f} % aller Tokens)")

    if all_errors:
        print(f"\n{len(all_errors)} Fehler:")
        for e in all_errors:
            print("  " + e)
        sys.exit(1)
    print("\nBIO-Sequenzen gueltig, keine Formatfehler.")
    sys.exit(0)


if __name__ == "__main__":
    main()

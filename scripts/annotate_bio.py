#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
annotate_bio.py (v2) -- erzeugt BIO-annotierte CoNLL-Dateien aus den Roh-Stellenanzeigen
und der manuellen Span-Liste (skill_spans.json).

Zwei unabhaengige Layer nach SkillSpan (Zhang et al., NAACL 2022):
  SKILL      -- Faehigkeiten und Taetigkeiten ("Betreuung von Bestandskunden")
  KNOWLEDGE  -- Werkzeuge, Technologien, Domaenen, Sprachen ("Python", "HGB", "Deutsch")

Ein KNOWLEDGE-Span darf innerhalb eines SKILL-Spans liegen; innerhalb eines Layers
sind Spans ueberlappungsfrei. Deshalb drei Ausgabevarianten:

  conll_skill/      Token + SKILL-Label        (2 Spalten)  -> Modelle mit layers=skill
  conll_knowledge/  Token + KNOWLEDGE-Label    (2 Spalten)  -> Modelle mit layers=knowledge
  conll_2layer/     Token + SKILL + KNOWLEDGE  (3 Spalten)  -> Multi-Task-Modelle

Aufruf:
    python3 annotate_bio.py --input <rohtext-dir> --spans skill_spans.json --out <output-dir>
"""

import argparse
import json
import os
import re
import sys
from collections import Counter

LAYERS = {"S": "SKILL", "K": "KNOWLEDGE"}

TOKEN_RE = re.compile(r"\w+(?:[-/.&+'\u2019]\w+)*|[^\w\s]", re.UNICODE)
SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ„\"])")
ABBREV = {
    "z", "B", "u", "a", "d", "h", "o", "Ä", "ca", "bzw", "inkl", "ggf", "päd",
    "std", "nr", "min", "vgl", "abs", "evtl", "engl", "ff", "dr", "prof", "etc",
}
ABBREV_TAIL_RE = re.compile(r"(\w+)\.$")
DASH_MAP = {"\u2010": "-", "\u2011": "-", "\u2012": "-", "\u00ad": "-"}


def normalize(text):
    for src, dst in DASH_MAP.items():
        text = text.replace(src, dst)
    return text.replace("\u00a0", " ")


def tokenize(text):
    return TOKEN_RE.findall(text)


def split_sentences(line):
    parts = [p.strip() for p in SENT_SPLIT_RE.split(line.strip()) if p.strip()]
    merged = []
    for part in parts:
        if merged:
            tail = ABBREV_TAIL_RE.search(merged[-1])
            if tail and tail.group(1).lower() in ABBREV:
                merged[-1] = merged[-1] + " " + part
                continue
        merged.append(part)
    return merged


def match_layer(tokens, span_token_lists, label, blocked):
    """BIO-Labels fuer EINEN Layer. Laengster Treffer zuerst, ueberlappungsfrei."""
    labels = ["O"] * len(tokens)
    lower = [t.lower() for t in tokens]
    matched = []
    i = 0
    while i < len(tokens):
        hit = None
        for span_text, span_tokens in span_token_lists:
            if span_text in blocked:
                continue
            n = len(span_tokens)
            if n == 0 or i + n > len(tokens):
                continue
            if lower[i:i + n] == span_tokens:
                hit = (span_text, n)
                break
        if hit:
            span_text, n = hit
            labels[i] = f"B-{label}"
            for k in range(1, n):
                labels[i + k] = f"I-{label}"
            matched.append((span_text, " ".join(tokens[i:i + n])))
            i += n
        else:
            i += 1
    return labels, matched


def process_document(doc_id, raw_text, config):
    skip_lines = set(config.get("skip_lines", []))
    blocked_by_line = {}
    for rule in config.get("block", []):
        blocked_by_line.setdefault(rule["line"], set()).add(rule["span"])

    by_layer = {"S": [], "K": []}
    for entry in config.get("spans", []):
        layer, surface = entry[0], entry[1]
        if layer not in by_layer:
            raise ValueError(f"{doc_id}: unbekannter Layer {layer!r}")
        by_layer[layer].append((surface, [t.lower() for t in tokenize(normalize(surface))]))
    for layer in by_layer:
        by_layer[layer].sort(key=lambda x: len(x[1]), reverse=True)

    sentences = []
    review_rows = []
    used = Counter()

    for line_no, raw_line in enumerate(raw_text.splitlines(), start=1):
        line = normalize(raw_line).strip()
        if not line:
            continue
        annotate = line_no not in skip_lines
        blocked = blocked_by_line.get(line_no, set())

        for sent_idx, sent in enumerate(split_sentences(line), start=1):
            tokens = tokenize(sent)
            if not tokens:
                continue
            if annotate:
                skill_labels, m_s = match_layer(tokens, by_layer["S"], "SKILL", blocked)
                know_labels, m_k = match_layer(tokens, by_layer["K"], "KNOWLEDGE", blocked)
                for layer, matches in (("SKILL", m_s), ("KNOWLEDGE", m_k)):
                    for span_text, surface in matches:
                        used[(layer, span_text)] += 1
                        review_rows.append((doc_id, line_no, layer, span_text, surface, sent))
            else:
                skill_labels = ["O"] * len(tokens)
                know_labels = ["O"] * len(tokens)
            sentences.append((f"{doc_id}-{line_no:04d}-{sent_idx}", sent, tokens,
                              skill_labels, know_labels))

    unused = []
    for layer_key, entries in by_layer.items():
        for surface, _ in entries:
            if used[(LAYERS[layer_key], surface)] == 0:
                unused.append((LAYERS[layer_key], surface))
    return sentences, review_rows, unused


def write_conll(path, doc_id, sentences, columns):
    """columns: Liste von Indizes (3 = skill, 4 = knowledge) aus dem Satz-Tupel."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# doc_id = {doc_id}\n")
        for sent in sentences:
            sent_id, text, tokens = sent[0], sent[1], sent[2]
            f.write(f"# sent_id = {sent_id}\n")
            f.write(f"# text = {text}\n")
            for i, tok in enumerate(tokens):
                cols = [tok] + [sent[c][i] for c in columns]
                f.write("\t".join(cols) + "\n")
            f.write("\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--spans", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.spans, encoding="utf-8") as f:
        cfg_all = json.load(f)

    variants = {"skill": [3], "knowledge": [4], "2layer": [3, 4]}
    for name in variants:
        os.makedirs(os.path.join(args.out, "conll_" + name), exist_ok=True)

    all_docs = []
    all_review = []
    all_unused = []
    stats = Counter()

    for fn in sorted(f for f in os.listdir(args.input) if f.endswith(".txt")):
        doc_id = os.path.splitext(fn)[0]
        if doc_id not in cfg_all:
            print(f"[WARN] keine Konfiguration fuer {doc_id}", file=sys.stderr)
        cfg = cfg_all.get(doc_id, {})
        with open(os.path.join(args.input, fn), encoding="utf-8") as f:
            raw = f.read()

        sentences, review, unused = process_document(doc_id, raw, cfg)
        for name, cols in variants.items():
            write_conll(os.path.join(args.out, "conll_" + name, doc_id + ".conll"),
                        doc_id, sentences, cols)
        all_docs.append((doc_id, sentences))
        all_review.extend(review)
        all_unused.extend((doc_id, l, s) for l, s in unused)

        stats["docs"] += 1
        stats["sentences"] += len(sentences)
        for _, _, tokens, sl, kl in sentences:
            stats["tokens"] += len(tokens)
            stats["B-SKILL"] += sl.count("B-SKILL")
            stats["I-SKILL"] += sl.count("I-SKILL")
            stats["B-KNOWLEDGE"] += kl.count("B-KNOWLEDGE")
            stats["I-KNOWLEDGE"] += kl.count("I-KNOWLEDGE")

    for name, cols in variants.items():
        with open(os.path.join(args.out, f"all_jobads_{name}.conll"), "w", encoding="utf-8") as f:
            for doc_id, sentences in all_docs:
                f.write(f"# doc_id = {doc_id}\n")
                for sent in sentences:
                    f.write(f"# sent_id = {sent[0]}\n")
                    f.write(f"# text = {sent[1]}\n")
                    for i, tok in enumerate(sent[2]):
                        f.write("\t".join([tok] + [sent[c][i] for c in cols]) + "\n")
                    f.write("\n")

    with open(os.path.join(args.out, "review_spans.tsv"), "w", encoding="utf-8") as f:
        f.write("doc_id\tzeile\tlayer\tspan_konfiguration\tannotierte_tokenfolge\tsatz\n")
        for row in all_review:
            f.write("\t".join(str(c) for c in row) + "\n")

    # Spanlaengen je Layer
    lengths = {"SKILL": Counter(), "KNOWLEDGE": Counter()}
    for doc_id, sentences in all_docs:
        for _, _, tokens, sl, kl in sentences:
            for labels, layer in ((sl, "SKILL"), (kl, "KNOWLEDGE")):
                cur = 0
                for lab in labels + ["O"]:
                    if lab.startswith("B-"):
                        if cur:
                            lengths[layer][cur] += 1
                        cur = 1
                    elif lab.startswith("I-"):
                        cur += 1
                    else:
                        if cur:
                            lengths[layer][cur] += 1
                        cur = 0

    print(f"Dokumente: {stats['docs']}   Saetze: {stats['sentences']}   Tokens: {stats['tokens']}")
    for layer in ("SKILL", "KNOWLEDGE"):
        n = sum(lengths[layer].values())
        tok = stats[f"B-{layer}"] + stats[f"I-{layer}"]
        single = lengths[layer][1]
        avg = tok / n if n else 0
        print(f"{layer:10s} Spans: {n:4d}   Tokens: {tok:4d}   Ein-Token-Spans: {single:3d} "
              f"({100.0*single/n:.0f} %)   Ø Laenge: {avg:.1f}")
    if all_unused:
        print("\n[HINWEIS] Spans ohne Treffer:")
        for doc_id, layer, surface in all_unused:
            print(f"  {doc_id} [{layer}]: {surface!r}")


if __name__ == "__main__":
    main()

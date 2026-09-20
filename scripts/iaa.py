#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iaa.py -- Inter-Annotator-Agreement zwischen zwei Annotationen desselben Korpus.

Annotator A: CoNLL-Datei mit drei Spalten (Token, SKILL, KNOWLEDGE)
Annotator B: JSON mit Zeichen-Offsets (schema_version 1.0)

Beide werden auf dieselbe Tokenfolge abgebildet und dann verglichen:

  Token-Ebene   Cohens kappa ueber die Labels {O, B-X, I-X} je Layer
  Span-Ebene    strikt   (identische Grenzen)
                gelockert (mindestens ein Token Ueberlappung)
                jeweils als F1 zwischen beiden Annotationen

Span-F1 ist hier symmetrisch: welcher Annotator "Referenz" ist, aendert den Wert
nicht. Cohens kappa auf Span-Ebene waere nicht definiert, weil es keine feste
Menge von Vergleichseinheiten gibt.

Aufruf:
    python3 iaa.py --conll all_jobads_2layer.conll --json annotationen.json --raw data/raw_de
"""

import argparse
import json
import os
import re
from collections import Counter, defaultdict

TOKEN_RE = re.compile(r"\w+(?:[-/.&+'\u2019]\w+)*|[^\w\s]", re.UNICODE)
DASH_MAP = {"\u2010": "-", "\u2011": "-", "\u2012": "-", "\u00ad": "-"}
LAYERS = ["SKILL", "KNOWLEDGE"]


def normalize(text):
    for src, dst in DASH_MAP.items():
        text = text.replace(src, dst)
    return text.replace("\u00a0", " ")


def tokenize_offsets(text):
    """Tokens mit Zeichen-Offsets. Gleiche Regex wie in annotate_bio.py."""
    return [(m.group(0), m.start(), m.end()) for m in TOKEN_RE.finditer(text)]


def read_conll(path):
    """Liest die 3-spaltige CoNLL-Datei, gruppiert nach doc_id."""
    docs = defaultdict(lambda: {"tokens": [], "SKILL": [], "KNOWLEDGE": []})
    doc_id = None
    for raw in open(path, encoding="utf-8"):
        line = raw.rstrip("\n")
        if line.startswith("# doc_id"):
            doc_id = line.split("=", 1)[1].strip()
            continue
        if line.startswith("#") or not line.strip():
            continue
        cols = line.split("\t")
        docs[doc_id]["tokens"].append(cols[0])
        docs[doc_id]["SKILL"].append(cols[1])
        docs[doc_id]["KNOWLEDGE"].append(cols[2])
    return docs


def spans_from_offsets(annotations, tokens, layer):
    """Zeichen-Offsets -> Token-Indizes -> BIO. Gibt (labels, spans) zurueck."""
    labels = ["O"] * len(tokens)
    spans = []
    for ann in annotations:
        if ann["label"] != layer:
            continue
        idx = [i for i, (_, s, e) in enumerate(tokens)
               if s >= ann["start"] and e <= ann["end"]]
        if not idx:
            continue
        a, b = idx[0], idx[-1] + 1
        # innerhalb eines Layers ueberlappungsfrei: erster Treffer gewinnt
        if any(labels[i] != "O" for i in range(a, b)):
            continue
        labels[a] = f"B-{layer}"
        for i in range(a + 1, b):
            labels[i] = f"I-{layer}"
        spans.append((a, b))
    return labels, sorted(spans)


def bio_to_spans(labels):
    out, i = [], 0
    while i < len(labels):
        if labels[i].startswith("B-"):
            j = i + 1
            while j < len(labels) and labels[j].startswith("I-"):
                j += 1
            out.append((i, j))
            i = j
        else:
            i += 1
    return out


def cohens_kappa(a, b):
    """Cohens kappa fuer zwei gleich lange Label-Folgen."""
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] / n * cb[k] / n for k in set(ca) | set(cb))
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def span_f1(spans_a, spans_b, relaxed=False):
    sa, sb = set(spans_a), set(spans_b)
    if relaxed:
        def overlaps(x, others):
            return any(x[0] == y[0] and x[1] < y[2] and y[1] < x[2] for y in others)
        tp_a = sum(overlaps(x, sb) for x in sa)
        tp_b = sum(overlaps(y, sa) for y in sb)
    else:
        tp_a = tp_b = len(sa & sb)
    p = tp_a / len(sa) if sa else 0.0
    r = tp_b / len(sb) if sb else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f, len(sa), len(sb)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--conll", required=True, help="3-spaltige CoNLL-Datei (Annotator A)")
    ap.add_argument("--json", required=True, help="Offset-JSON (Annotator B)")
    ap.add_argument("--raw", required=True, help="Verzeichnis mit den Rohtexten")
    ap.add_argument("--dump", help="TSV mit allen Abweichungen auf Span-Ebene")
    args = ap.parse_args()

    conll = read_conll(args.conll)
    data = json.load(open(args.json, encoding="utf-8"))

    tok_a = {l: [] for l in LAYERS}
    tok_b = {l: [] for l in LAYERS}
    spn_a = {l: [] for l in LAYERS}
    spn_b = {l: [] for l in LAYERS}
    rows = []

    for doc in data["documents"]:
        doc_id = os.path.splitext(os.path.basename(doc["source_file"]))[0]
        if doc_id not in conll:
            print(f"[WARN] {doc_id} fehlt in der CoNLL-Datei")
            continue
        text = normalize(doc["text"])
        tokens = tokenize_offsets(text)
        c = conll[doc_id]

        if [t[0] for t in tokens] != c["tokens"]:
            print(f"[WARN] {doc_id}: Tokenfolgen weichen ab "
                  f"({len(tokens)} vs. {len(c['tokens'])}) — uebersprungen")
            continue

        for layer in LAYERS:
            lab_b, sp_b = spans_from_offsets(doc["annotations"], tokens, layer)
            lab_a = c[layer]
            sp_a = bio_to_spans(lab_a)

            tok_a[layer] += lab_a
            tok_b[layer] += lab_b
            spn_a[layer] += [(doc_id,) + s for s in sp_a]
            spn_b[layer] += [(doc_id,) + s for s in sp_b]

            if args.dump:
                sa, sb = set(sp_a), set(sp_b)
                for s in sorted(sa - sb):
                    rows.append((doc_id, layer, "nur A", " ".join(t[0] for t in tokens[s[0]:s[1]])))
                for s in sorted(sb - sa):
                    rows.append((doc_id, layer, "nur B", " ".join(t[0] for t in tokens[s[0]:s[1]])))

    print("=" * 66)
    print("INTER-ANNOTATOR-AGREEMENT")
    print("=" * 66)
    for layer in LAYERS:
        k = cohens_kappa(tok_a[layer], tok_b[layer])
        agr = sum(x == y for x, y in zip(tok_a[layer], tok_b[layer])) / len(tok_a[layer])
        ps, rs, fs, na, nb = span_f1(spn_a[layer], spn_b[layer], relaxed=False)
        pr, rr, fr, _, _ = span_f1(spn_a[layer], spn_b[layer], relaxed=True)
        print(f"\n{layer}")
        print(f"  Tokens                {len(tok_a[layer])}")
        print(f"  Spans A / B           {na} / {nb}")
        print(f"  Token-Uebereinstimmung {agr:.4f}")
        print(f"  Cohens kappa (Token)   {k:.4f}")
        print(f"  Span-F1 strikt         {fs:.4f}   (P {ps:.4f} / R {rs:.4f})")
        print(f"  Span-F1 gelockert      {fr:.4f}   (P {pr:.4f} / R {rr:.4f})")

    if args.dump:
        with open(args.dump, "w", encoding="utf-8") as f:
            f.write("doc_id\tlayer\tnur_bei\tspan\n")
            for r in rows:
                f.write("\t".join(r) + "\n")
        print(f"\n{len(rows)} Abweichungen geschrieben nach {args.dump}")


if __name__ == "__main__":
    main()

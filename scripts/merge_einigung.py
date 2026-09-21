#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
merge_einigung.py -- baut das finale deutsche Testset aus
  (a) den Spans, bei denen Annotator A und B bereits exakt uebereinstimmten, und
  (b) den im Abgleich entschiedenen Spans (einigungsfassung.tsv).

Die Einigungsfassung nennt Spans nur ueber ihre Tokenfolge, nicht ueber ihre Position.
Jede Zeile wird deshalb derjenigen Fundstelle im Dokument zugeordnet, die mit einem
strittigen Span (nur A / nur B) desselben Layers ueberlappt. Gibt es keine solche
Fundstelle, wird eine eindeutige, konfliktfreie Fundstelle genommen; alles andere
wird als ungeklaert gemeldet und NICHT stillschweigend geraten.

Ausgabe:
  final_2layer.conll / final_skill.conll / final_knowledge.conll
  final_annotation.json   (Zeichen-Offsets, gleiches Schema wie die Zweitannotation)
  merge_protokoll.tsv     (jede Einigungszeile mit Position und Zuordnungsart)
"""

import argparse
import csv
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from iaa import (LAYERS, bio_to_spans, normalize, read_conll,  # noqa: E402
                 spans_from_offsets, tokenize_offsets)


def find_occurrences(tokens, seq):
    n = len(seq)
    words = [t[0] for t in tokens]
    return [(i, i + n) for i in range(len(words) - n + 1) if words[i:i + n] == seq]


def overlaps(a, b):
    return a[0] < b[1] and b[0] < a[1]


def to_bio(spans, n, layer):
    labels = ["O"] * n
    for a, b in spans:
        labels[a] = f"B-{layer}"
        for i in range(a + 1, b):
            labels[i] = f"I-{layer}"
    return labels


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--conll", required=True, help="Annotation A (3-spaltig)")
    ap.add_argument("--json", required=True, help="Annotation B (Offset-JSON)")
    ap.add_argument("--einigung", required=True, help="einigungsfassung.tsv")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    conll = read_conll(args.conll)
    data = json.load(open(args.json, encoding="utf-8"))
    einigung = list(csv.DictReader(open(args.einigung, encoding="utf-8-sig"), delimiter="\t"))

    rows_by_doc = defaultdict(list)
    for r in einigung:
        rows_by_doc[r["doc_id"].strip()].append(r)

    # CoNLL, satzweise wie im Original (Satzgrenzen aus Annotation A uebernehmen)
    sent_bounds = defaultdict(list)
    doc_id, idx = None, 0
    for raw in open(args.conll, encoding="utf-8"):
        line = raw.rstrip("\n")
        if line.startswith("# doc_id"):
            doc_id, idx = line.split("=", 1)[1].strip(), 0
            continue
        if line.startswith("# sent_id"):
            sent_bounds[doc_id].append([line.split("=", 1)[1].strip(), idx, idx])
            continue
        if line.startswith("#") or not line.strip():
            continue
        sent_bounds[doc_id][-1][2] += 1
        idx += 1


    final_docs = []
    protokoll = []
    stats = defaultdict(int)

    for doc in data["documents"]:
        doc_id = os.path.splitext(os.path.basename(doc["source_file"]))[0]
        text = normalize(doc["text"])
        tokens = tokenize_offsets(text)
        c = conll[doc_id]
        assert [t[0] for t in tokens] == c["tokens"], doc_id

        chosen = {}
        for layer in LAYERS:
            sp_a = set(bio_to_spans(c[layer]))
            _, sp_b = spans_from_offsets(doc["annotations"], tokens, layer)
            sp_b = set(sp_b)
            agreed = sp_a & sp_b
            disputed = (sp_a | sp_b) - agreed
            chosen[layer] = set(agreed)
            stats[f"{layer}_einig_vorab"] += len(agreed)

            for r in rows_by_doc.get(doc_id, []):
                if r["layer"].strip() != layer:
                    continue
                seq = r["span"].strip().split(" ")
                occ = find_occurrences(tokens, seq)
                if not occ:
                    protokoll.append((doc_id, layer, r["span"], "", "NICHT GEFUNDEN"))
                    stats["nicht_gefunden"] += 1
                    continue
                # schon vorhanden (z.B. "neu aus Umgang mit ...; pruefen, ob schon vorhanden")
                if any(o in chosen[layer] for o in occ) and \
                        not any(any(overlaps(o, d) for d in disputed) and o not in chosen[layer]
                                for o in occ):
                    protokoll.append((doc_id, layer, r["span"], "", "bereits vorhanden"))
                    stats["duplikat"] += 1
                    continue
                free = [o for o in occ if not any(overlaps(o, s) for s in chosen[layer])]
                herkunft = r["herkunft"].strip()
                if herkunft in ("wie A", "A=B"):
                    exact = [o for o in free if o in sp_a]
                elif herkunft == "wie B":
                    exact = [o for o in free if o in sp_b]
                else:
                    exact = []
                near = [o for o in free if any(overlaps(o, d) for d in disputed)]
                if exact:
                    pick, how = exact[0], f"exakt {herkunft}"
                elif near:
                    pick, how = near[0], "am strittigen Span"
                elif len(free) == 1:
                    pick, how = free[0], "eindeutige Fundstelle"
                else:
                    protokoll.append((doc_id, layer, r["span"], "",
                                      f"UNGEKLAERT ({len(free)} freie Fundstellen)"))
                    stats["ungeklaert"] += 1
                    continue
                chosen[layer].add(pick)
                stats[f"{layer}_aus_einigung"] += 1
                protokoll.append((doc_id, layer, r["span"],
                                  f"{tokens[pick[0]][1]}-{tokens[pick[1]-1][2]}", how))

        # Spans duerfen keine Satzgrenze ueberqueren (Richtlinie, Abschnitt 5):
        # ueber einen Zeilenumbruch laufende Spans werden an der Grenze geteilt.
        starts = {a for _, a, _ in sent_bounds[doc_id]}
        for l in LAYERS:
            split = set()
            for a, b in chosen[l]:
                cut = sorted(x for x in starts if a < x < b)
                if cut:
                    edges = [a] + cut + [b]
                    for x, y in zip(edges, edges[1:]):
                        split.add((x, y))
                    protokoll.append((doc_id, l, " ".join(t[0] for t in tokens[a:b]), "",
                                      f"an Satzgrenze geteilt ({len(cut)+1} Teile)"))
                    stats["an_satzgrenze_geteilt"] += 1
                else:
                    split.add((a, b))
            chosen[l] = split
        labels = {l: to_bio(sorted(chosen[l]), len(tokens), l) for l in LAYERS}
        anns = []
        for l in LAYERS:
            for a, b in sorted(chosen[l]):
                s, e = tokens[a][1], tokens[b - 1][2]
                anns.append({"label": l, "start": s, "end": e, "text": text[s:e]})
        anns.sort(key=lambda x: (x["start"], x["label"]))
        final_docs.append((doc_id, doc, tokens, labels, anns))

    variants = {"2layer": LAYERS, "skill": ["SKILL"], "knowledge": ["KNOWLEDGE"]}
    for name, lays in variants.items():
        with open(os.path.join(args.out, f"final_{name}.conll"), "w", encoding="utf-8") as f:
            for doc_id, doc, tokens, labels, _ in final_docs:
                f.write(f"# doc_id = {doc_id}\n")
                for sid, a, b in sent_bounds[doc_id]:
                    f.write(f"# sent_id = {sid}\n")
                    for i in range(a, b):
                        f.write("\t".join([tokens[i][0]] + [labels[l][i] for l in lays]) + "\n")
                    f.write("\n")

    out_json = {
        "schema_version": "1.0",
        "annotation_layers": LAYERS,
        "offset_convention": "zero-based, end-exclusive, bezogen auf normalisierten Text",
        "documents": [
            {"id": doc["id"], "source_file": doc["source_file"], "text": doc["text"], "annotations": anns}
            for _, doc, _, _, anns in final_docs
        ],
    }
    json.dump(out_json, open(os.path.join(args.out, "final_annotation.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    with open(os.path.join(args.out, "merge_protokoll.tsv"), "w", encoding="utf-8") as f:
        f.write("doc_id\tlayer\tspan\tposition\tzuordnung\n")
        for r in protokoll:
            f.write("\t".join(r) + "\n")

    print("Zuordnung der Einigungszeilen:")
    for k in sorted(stats):
        print(f"  {k:24s} {stats[k]}")
    for l in LAYERS:
        n = sum(len([1 for x in lab[l] if x.startswith("B-")]) for _, _, _, lab, _ in final_docs)
        toks = sum(len([1 for x in lab[l] if x != "O"]) for _, _, _, lab, _ in final_docs)
        print(f"{l:10s} Spans final: {n:4d}   Span-Tokens: {toks:5d}   Ø Laenge: {toks/n:.2f}")


if __name__ == "__main__":
    main()

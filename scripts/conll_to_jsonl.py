#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
conll_to_jsonl.py -- wandelt die 3-spaltige CoNLL-Datei (Token, SKILL, KNOWLEDGE)
in das jsonl-Format der Trainingspipeline um.

Aufruf:
    python3 conll_to_jsonl.py all_jobads_2layer.conll data/processed_de/test.jsonl
"""

import json
import sys


def read_conll(path):
    sents = []
    cur = {"tokens": [], "skill_tags": [], "knowledge_tags": []}
    doc_id = None
    for raw in open(path, encoding="utf-8"):
        line = raw.rstrip("\n")
        if line.startswith("# doc_id"):
            doc_id = line.split("=", 1)[1].strip()
            continue
        if line.startswith("#"):
            continue
        if not line.strip():
            if cur["tokens"]:
                cur["doc_id"] = doc_id
                sents.append(cur)
                cur = {"tokens": [], "skill_tags": [], "knowledge_tags": []}
            continue
        cols = line.split("\t")
        if len(cols) != 3:
            raise SystemExit(f"{path}: erwarte 3 Spalten, gefunden {len(cols)}: {line!r}")
        cur["tokens"].append(cols[0])
        cur["skill_tags"].append(cols[1])
        cur["knowledge_tags"].append(cols[2])
    if cur["tokens"]:
        cur["doc_id"] = doc_id
        sents.append(cur)
    return sents


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Aufruf: conll_to_jsonl.py <eingabe.conll> <ausgabe.jsonl>")
    src, dst = sys.argv[1], sys.argv[2]
    sents = read_conll(src)

    doc_order = []
    for s in sents:
        if s["doc_id"] not in doc_order:
            doc_order.append(s["doc_id"])

    with open(dst, "w", encoding="utf-8") as f:
        for i, s in enumerate(sents):
            rec = {
                "id": f"test_{i}",
                "doc_idx": doc_order.index(s["doc_id"]) + 1,
                "source": "de_jobads",
                "tokens": s["tokens"],
                "skill_tags": s["skill_tags"],
                "knowledge_tags": s["knowledge_tags"],
                "seen_in_train": False,
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    n_skill = sum(t.startswith("B-") for s in sents for t in s["skill_tags"])
    n_know = sum(t.startswith("B-") for s in sents for t in s["knowledge_tags"])
    print(f"{len(sents)} Saetze, {len(doc_order)} Dokumente -> {dst}")
    print(f"SKILL-Spans: {n_skill}   KNOWLEDGE-Spans: {n_know}")


if __name__ == "__main__":
    main()

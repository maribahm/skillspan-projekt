#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_predictions.py -- baut das Speichern der Testvorhersagen ein.

Aendert zwei Dateien, jeweils nur an eindeutig gepruefter Stelle:
  src/dataset.py     evaluate() merkt sich die Satzindizes; neue Funktion save_predictions()
  scripts/train.py   Testvorhersagen werden nicht mehr verworfen, sondern gespeichert

Danach schreibt jeder Lauf eine Datei nach
  results/predictions/<config>_<datenordner>_seed<seed>.jsonl
mit Tokens, Gold- und vorhergesagten Tags pro Satz.

Das Skript bricht ab, ohne etwas zu veraendern, wenn eine Stelle nicht exakt passt,
und laesst sich nicht doppelt anwenden.

Aufruf (im Projektordner):  python3 scripts/patch_predictions.py
"""

import sys

DS = "src/dataset.py"
TR = "scripts/train.py"

ds = open(DS, encoding="utf-8").read()
tr = open(TR, encoding="utf-8").read()

if "def save_predictions" in ds:
    sys.exit("Bereits gepatcht, nichts zu tun.")

edits_ds = [
    ("    pred = {l: [] for l in layers}\n",
     "    pred = {l: [] for l in layers}\n    index = []\n"),
    ("                pred[l].append(tags)\n",
     "                if l == layers[0]:\n                    index.append(i)\n"
     "                pred[l].append(tags)\n"),
    ("    return results, gold, pred\n",
     "    pred[\"_index\"] = index\n    return results, gold, pred\n"),
]
edits_tr = [
    ("from dataset import SpanDataset, evaluate, make_collate  # noqa: E402\n",
     "from dataset import SpanDataset, evaluate, make_collate, save_predictions  # noqa: E402\n"),
    ("    test, _, _ = evaluate(model, loaders[\"test\"], sets[\"test\"], labels, layers, device)\n",
     "    test, gold_test, pred_test = evaluate(model, loaders[\"test\"], sets[\"test\"], labels, layers, device)\n"
     "    save_predictions(sets[\"test\"], gold_test, pred_test, layers)\n"),
]

for path, text, edits in [(DS, ds, edits_ds), (TR, tr, edits_tr)]:
    for old, _ in edits:
        n = text.count(old)
        if n != 1:
            sys.exit(f"Abbruch: Stelle in {path} {n}-mal gefunden (erwartet genau 1):\n{old}")

for old, new in edits_ds:
    ds = ds.replace(old, new, 1)
for old, new in edits_tr:
    tr = tr.replace(old, new, 1)

ds += '''

def save_predictions(dataset, gold, pred, layers, out_dir="results/predictions"):
    """Schreibt Tokens, Gold- und vorhergesagte Tags pro Testsatz als jsonl."""
    import json
    import os
    import sys

    argv = sys.argv

    def arg(name, default=""):
        return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else default

    cfg = os.path.splitext(os.path.basename(arg("--config", "run")))[0]
    seed = arg("--seed", "noseed")
    data = os.path.basename(arg("--data", "processed").rstrip("/"))
    smoke = "_smoke" if "--smoke" in argv else ""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{cfg}_{data}_seed{seed}{smoke}.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for k, i in enumerate(pred["_index"]):
            row = dataset.rows[i]
            rec = {"id": row.get("id", i), "tokens": row["tokens"],
                   "seen_in_train": row.get("seen_in_train")}
            for l in layers:
                rec[f"gold_{l}"] = gold[l][k]
                rec[f"pred_{l}"] = pred[l][k]
            f.write(json.dumps(rec, ensure_ascii=False) + "\\n")
    print(f"Vorhersagen gespeichert: {path}")
'''

open(DS, "w", encoding="utf-8").write(ds)
open(TR, "w", encoding="utf-8").write(tr)
print("Gepatcht: src/dataset.py, scripts/train.py")

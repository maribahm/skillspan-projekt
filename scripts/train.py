"""
Training und Evaluation eines Modells.

Alle Einstellungen kommen aus einer JSON-Config in configs/, damit jedes
Experiment reproduzierbar ist und ihr die Ablationen nur ueber Configs steuert.

Aufruf:
  python scripts/train.py --config configs/bert_linear_skill.json --seed 1
  python scripts/train.py --config configs/bert_linear_skill.json --seed 1 --smoke

--smoke trainiert auf nur 20 Saetzen. Wenn das Modell die nicht fast auswendig
lernt (F1 nahe 1.0), stimmt etwas in der Pipeline nicht -> IMMER zuerst laufen lassen.

Ausgabe:
  results/<name>_seed<seed>.json   alle Metriken
  results/all_runs.csv             eine Zeile pro Lauf, zum Vergleichen
"""
import argparse
import csv
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader
from transformers import AutoTokenizer, get_linear_schedule_with_warmup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from data import load_labels, load_split  # noqa: E402
from dataset import SpanDataset, evaluate, make_collate  # noqa: E402
from model import SpanTagger  # noqa: E402


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--seed", type=int, default=3477689,
                    help="Das Paper nutzt 3477689 4213916 8749520 6828303 9364029")
    ap.add_argument("--data", default=str(ROOT / "data/processed"))
    ap.add_argument("--out", default=str(ROOT / "results"))
    ap.add_argument("--smoke", action="store_true", help="Sanity-Check auf 20 Saetzen")
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text())
    set_seed(args.seed)
    device = ("cuda" if torch.cuda.is_available()
              else "mps" if torch.backends.mps.is_available() else "cpu")
    print(f"Config: {cfg['name']} | Seed: {args.seed} | Device: {device}")

    data_dir = Path(args.data)
    labels = load_labels(data_dir / "labels.json")
    layers = cfg["layers"]
    extra = {"add_prefix_space": True} if "roberta" in cfg["model"] and "xlm" not in cfg["model"] else {}
    tok = AutoTokenizer.from_pretrained(cfg["model"], use_fast=True, **extra)

    splits = {s: load_split(data_dir / f"{s}.jsonl") for s in ["train", "dev", "test"]}
    if args.smoke:
        # Saetze MIT Span nehmen, sonst lernt das Modell nur "alles O"
        splits["train"] = [r for r in splits["train"]
                           if all(any(t != "O" for t in r[f"{l}_tags"]) for l in layers)][:20]
        splits["dev"] = splits["test"] = splits["train"]
        cfg["epochs"] = 60
        cfg["batch_size"] = 4     # mehr Schritte pro Epoche als bei 32
        cfg["lr"] = 1e-4
        cfg["warmup_ratio"] = 0.0

    sets = {s: SpanDataset(rows, tok, labels, layers, cfg.get("strategy", "first"),
                           cfg.get("max_length", 256)) for s, rows in splits.items()}
    collate = make_collate(tok.pad_token_id, layers)
    loaders = {s: DataLoader(ds, batch_size=cfg["batch_size"], shuffle=(s == "train"),
                             collate_fn=collate) for s, ds in sets.items()}

    model = SpanTagger(cfg["model"], layers,
                       id2label={l: labels[l]["id2label"] for l in layers},
                       decoder=cfg.get("decoder", "crf"),
                       dropout=cfg.get("dropout", 0.2),
                       freeze_encoder=cfg.get("freeze_encoder", False),
                       constrain_bio=cfg.get("constrain_bio", True)).to(device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg["lr"],
                                  betas=tuple(cfg.get("betas", [0.9, 0.999])),
                                  weight_decay=cfg.get("weight_decay", 0.01))
    total_steps = len(loaders["train"]) * cfg["epochs"]
    scheduler = get_linear_schedule_with_warmup(
        optimizer, int(total_steps * cfg.get("warmup_ratio", 0.1)), total_steps)

    best = {"f1": -1.0, "epoch": 0, "state": None}
    history, start = [], time.time()

    for epoch in range(1, cfg["epochs"] + 1):
        model.train()
        total = 0.0
        for batch in loaders["train"]:
            optimizer.zero_grad()
            _, loss = model(batch["input_ids"].to(device), batch["attention_mask"].to(device),
                            {l: batch[f"labels_{l}"].to(device) for l in layers})
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.get("max_grad_norm", 1.0))
            optimizer.step()
            scheduler.step()
            total += loss.item()
        train_loss = total / len(loaders["train"])

        dev, _, _ = evaluate(model, loaders["dev"], sets["dev"], labels, layers, device)
        mean_f1 = sum(dev[l]["f1"] for l in layers) / len(layers)
        history.append({"epoch": epoch, "train_loss": train_loss,
                        **{f"dev_f1_{l}": dev[l]["f1"] for l in layers}})
        print(f"  Epoche {epoch}: loss={train_loss:.4f} | " +
              " | ".join(f"dev-F1 {l}={dev[l]['f1']:.4f}" for l in layers))

        if mean_f1 > best["f1"]:  # bestes Modell nach Dev-F1 behalten
            best = {"f1": mean_f1, "epoch": epoch,
                    "state": {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}}

    print(f"Bestes Modell: Epoche {best['epoch']} (Dev-F1 {best['f1']:.4f})")
    model.load_state_dict(best["state"])

    test, _, _ = evaluate(model, loaders["test"], sets["test"], labels, layers, device)
    # Zusatzauswertung: nur Saetze, die NICHT identisch im Train-Set stehen
    unseen = [not r.get("seen_in_train", False) for r in splits["test"]]
    test_unseen, _, _ = evaluate(model, loaders["test"], sets["test"], labels, layers, device, subset=unseen)

    for l in layers:
        print(f"\n=== TEST {l} ===\n{test[l]['report']}")
        print(f"nur ungesehene Saetze: F1={test_unseen[l]['f1']:.4f}")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {"config": cfg, "seed": args.seed, "best_epoch": best["epoch"],
              "minutes": round((time.time() - start) / 60, 1), "history": history,
              "dev_f1": best["f1"],
              "test": {l: {k: v for k, v in test[l].items() if k != "report"} for l in layers},
              "test_unseen": {l: {"f1": test_unseen[l]["f1"]} for l in layers}}
    (out_dir / f"{cfg['name']}_seed{args.seed}.json").write_text(json.dumps(result, indent=2))

    csv_path = out_dir / "all_runs.csv"
    row = {"name": cfg["name"], "model": cfg["model"], "decoder": cfg.get("decoder", "crf"),
           "layers": "+".join(layers), "strategy": cfg.get("strategy", "first"),
           "seed": args.seed, "best_epoch": best["epoch"], "minutes": result["minutes"]}
    for l in layers:
        row[f"test_p_{l}"] = round(test[l]["precision"], 4)
        row[f"test_r_{l}"] = round(test[l]["recall"], 4)
        row[f"test_f1_{l}"] = round(test[l]["f1"], 4)
        row[f"test_f1_unseen_{l}"] = round(test_unseen[l]["f1"], 4)
    exists = csv_path.exists()
    with open(csv_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(row))
        if not exists:
            writer.writeheader()
        writer.writerow(row)
    print(f"\nGespeichert: {csv_path}")


if __name__ == "__main__":
    main()

"""Dataset, Batch-Bildung (Padding) und Evaluation auf Span-Ebene."""
import sys
from pathlib import Path

import torch
from seqeval.metrics import classification_report, f1_score, precision_score, recall_score
from torch.utils.data import Dataset

sys.path.insert(0, str(Path(__file__).resolve().parent))
from data import encode, to_word_level  # noqa: E402

IGNORE = -100


class SpanDataset(Dataset):
    def __init__(self, rows, tokenizer, labels, layers, strategy="first", max_length=256):
        self.rows, self.layers, self.labels = rows, layers, labels
        self.encoded = [encode(r, tokenizer, labels, strategy, max_length) for r in rows]

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, i):
        enc, row = self.encoded[i], self.rows[i]
        item = {"input_ids": enc["input_ids"], "attention_mask": enc["attention_mask"],
                "word_ids": enc["word_ids"], "index": i, "n_words": len(row["tokens"])}
        for l in self.layers:
            item[f"labels_{l}"] = enc[f"labels_{l}"]
        return item


def make_collate(pad_id, layers):
    """Fuellt alle Sequenzen eines Batches auf dieselbe Laenge auf."""
    def collate(batch):
        n = max(len(b["input_ids"]) for b in batch)
        out = {"index": torch.tensor([b["index"] for b in batch]),
               "n_words": torch.tensor([b["n_words"] for b in batch])}
        out["input_ids"] = torch.tensor([b["input_ids"] + [pad_id] * (n - len(b["input_ids"])) for b in batch])
        out["attention_mask"] = torch.tensor([b["attention_mask"] + [0] * (n - len(b["attention_mask"])) for b in batch])
        out["word_ids"] = torch.tensor([b["word_ids"] + [-1] * (n - len(b["word_ids"])) for b in batch])
        for l in layers:
            key = f"labels_{l}"
            out[key] = torch.tensor([b[key] + [IGNORE] * (n - len(b[key])) for b in batch])
        return out
    return collate


@torch.no_grad()
def evaluate(model, loader, dataset, labels, layers, device, subset=None):
    """Entity-level Precision/Recall/F1 mit seqeval (nicht Token-Accuracy!).

    subset: optionale Liste von Booleans pro Satz, z. B. um nur Saetze zu
            bewerten, die nicht identisch im Train-Set stehen.
    """
    model.eval()
    gold = {l: [] for l in layers}
    pred = {l: [] for l in layers}
    for batch in loader:
        ids = batch["input_ids"].to(device)
        att = batch["attention_mask"].to(device)
        label_mask = (batch[f"labels_{layers[0]}"] != IGNORE).to(device)
        out = model.predict(ids, att, label_mask)
        for l in layers:
            for b in range(ids.size(0)):
                i = int(batch["index"][b])
                if subset is not None and not subset[i]:
                    continue
                word_ids = [None if w == -1 else w for w in batch["word_ids"][b].tolist()]
                tags = to_word_level(out[l][b].tolist(), word_ids, int(batch["n_words"][b]),
                                     labels[l]["id2label"])
                pred[l].append(tags)
                gold[l].append(dataset.rows[i][f"{l}_tags"])
    results = {}
    for l in layers:
        results[l] = {"precision": precision_score(gold[l], pred[l]),
                      "recall": recall_score(gold[l], pred[l]),
                      "f1": f1_score(gold[l], pred[l]),
                      "report": classification_report(gold[l], pred[l], digits=4, zero_division=0)}
    return results, gold, pred

# Skill Extraction from Job Postings

Re-Implementierung von **SkillSpan** (Zhang et al., NAACL 2022) mit eigenen Ablationen und
einem Transfer-Experiment auf deutsche Stellenanzeigen.

Projekt im Kurs Information Extraction, SoSe 2026 — Nigina Fazel und Marib Ahmad.

## Referenz

```
@inproceedings{zhang-etal-2022-skillspan,
    title = "{S}kill{S}pan: Hard and Soft Skill Extraction from {E}nglish Job Postings",
    author = "Zhang, Mike and Jensen, Kristian N{\o}rgaard and Sonniks, Sif and Plank, Barbara",
    booktitle = "Proceedings of the 2022 Conference of the North American Chapter of the
                 Association for Computational Linguistics: Human Language Technologies",
    month = jul, year = "2022", address = "Seattle, United States",
    publisher = "Association for Computational Linguistics",
    url = "https://aclanthology.org/2022.naacl-main.366", pages = "4962--4984",
}
```

Code und Daten: https://github.com/kris927b/SkillSpan (MIT) · Modelle: https://huggingface.co/jjzha

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/prepare_data.py                              # Rohdaten -> data/processed/
python scripts/check_alignment.py --model bert-base-cased   # muss "Alignment OK" ausgeben
```

## Erster Lauf: Sanity-Check

```bash
python scripts/train.py --config configs/bert_skill.json --smoke
```

Trainiert 60 Epochen auf 20 Saetzen, die alle mindestens einen Span enthalten. Der
**train_loss muss deutlich fallen und dev-F1 klar steigen** — das Modell soll diese 20 Saetze
auswendig lernen. Passiert das nicht, ist etwas in der Pipeline kaputt und ein richtiges
Training waere Zeitverschwendung.

## Experimente

```bash
python scripts/train.py --config configs/jobbert_skill.json --seed 3477689
```

Das Paper nutzt fuenf Seeds: `3477689 4213916 8749520 6828303 9364029`. Berichtet Mittelwert
und Standardabweichung — viele Unterschiede zwischen Modellen sind kleiner als die Schwankung
zwischen Seeds. Wenn die Rechenzeit nicht reicht, mindestens drei Seeds.

**Reproduktion** (wie im Paper: CRF-Decoder, single-task):

| Config | Encoder |
|---|---|
| `bert_skill`, `bert_knowledge` | `bert-base-cased` |
| `jobbert_skill`, `jobbert_knowledge` | `jjzha/jobbert-base-cased` (dom&auml;nenangepasst) |
| `spanbert_skill` | `jjzha/spanbert-base-cased` (auf lange Spans optimiert) |
| `jobspanbert_skill` | `jjzha/jobspanbert-base-cased` |
| `bert_multi`, `jobbert_multi` | Multi-Task: Skills und Knowledge gemeinsam |

**Eigene Ablationen:**

| Config | Frage |
|---|---|
| `*_skill_linear` | Wie viel bringt der CRF gegen&uuml;ber unabh&auml;ngiger Token-Klassifikation? |
| `jobbert_skill_crf_unconstrained` | Wie viel davon kommt allein aus den BIO-Constraints? |
| `jobbert_skill_allsub` | Erstes Subword labeln vs. alle Subwords |
| `jobbert_skill_frozen` | Volles Fine-Tuning vs. eingefrorener Encoder |
| `jobbert_skill_len128` | Effekt der K&uuml;rzung auf 128 Subwords (Wert des Papers) |

**Transfer ins Deutsche:** `xlmr_skill`, `xlmr_multi` auf Englisch trainieren, dann ohne
weiteres Training auf dem selbst annotierten deutschen Testset evaluieren.

Ergebnisse landen in `results/all_runs.csv` (eine Zeile pro Lauf) und als JSON pro Lauf.

## Auf Kaggle laufen lassen

Auf dem Laptop dauert ein Lauf Stunden. Auf Kaggle (Settings -> Accelerator -> GPU T4):

```python
!git clone https://github.com/maribahm/skillspan-projekt.git
%cd skillspan-projekt
!pip install -q seqeval
!python scripts/train.py --config configs/jobbert_skill.json --seed 3477689
```

Bei einem privaten Repo einen GitHub-Token verwenden oder das Projekt als Kaggle-Dataset
hochladen. Ergebnisse (`results/`) danach herunterladen und ins Repo committen.

## Hyperparameter und Abweichungen vom Original

Die Werte in `configs/` stammen aus den Original-Configs des SkillSpan-Repos
(`configs/bert.json` usw.): 20 Epochen, Batch 32, AdamW mit lr 1e-4, betas (0.9, 0.99),
weight decay 0.01, Dropout 0.2, CRF-Decoder mit BIO-Constraints.

Bewusste Abweichungen, die im Bericht begruendet werden muessen:

1. **Learning-Rate-Schedule.** Das Original nutzt MaChAmp mit slanted triangular schedule,
   discriminative fine-tuning und gradual unfreezing. Hier: linearer Warmup (30 %) mit
   linearem Abfall. Einfacher und nachvollziehbarer, aber nicht identisch.
2. **Maximale Laenge.** Das Original kuerzt bei 128 Subwords. Hier 256, dafuer werden lange
   Trainingssaetze vorher an Span-Grenzen geteilt (`prepare_data.py`), sodass nichts
   verloren geht. `jobbert_skill_len128` misst den Effekt.
3. **Datenmenge.** Nur zwei der drei Teilmengen sind veroeffentlicht, die Zahlen sind daher
   nicht direkt mit der Papertabelle vergleichbar.
4. **Eigene CRF-Implementierung** statt der AllenNLP-Variante aus MaChAmp — mit denselben
   BIO-Constraints (`allowed_transitions('BIO', ...)`).

## Aufbau

```
configs/         eine JSON-Datei pro Experiment (alle Hyperparameter)
data/raw/        Originaldaten von github.com/kris927b/SkillSpan (MIT)
data/processed/  aufbereitete Daten (erzeugt von prepare_data.py)
scripts/         prepare_data.py, check_alignment.py, train.py
src/             data.py (Alignment), dataset.py (Batches, Evaluation), model.py (Encoder, CRF)
results/         Metriken pro Lauf + all_runs.csv
```

Details zu den Daten und ihren Auffaelligkeiten: siehe `DATEN.md`.

## Hinweis zur Evaluation

Gemessen wird **entity-level F1 mit seqeval**, nicht Token-Accuracy. Ein Span zaehlt nur als
richtig, wenn Anfang, Ende und Typ stimmen. Token-Accuracy waere irrefuehrend hoch, weil rund
zwei Drittel der Saetze gar keinen Span enthalten.

`all_runs.csv` enthaelt zusaetzlich `test_f1_unseen_*`: F1 nur auf Test-Saetzen, die nicht
identisch im Train-Set vorkommen (812 der 3.569 Test-Saetze sind Wiederholungen, meist
Boilerplate wie "Job description:").

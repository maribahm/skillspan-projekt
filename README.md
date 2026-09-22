# Skill Extraction from Job Postings

Re-Implementierung von **SkillSpan** (Zhang et al., NAACL 2022) mit eigenen Ablationen und
einem Zero-Shot-Transfer auf ein selbst annotiertes deutsches Testset.

Projekt im Kurs Information Extraction, SoSe 2026 — Nigina Fazel und Marib Ahmad.

## Überblick

Die Aufgabe ist Sequence Labeling mit BIO-Tags auf zwei unabhängigen Ebenen: **SKILL**
(Fähigkeiten und Tätigkeiten) und **KNOWLEDGE** (Werkzeuge, Technologien, Domänen,
Sprachen). Ein Encoder (BERT, JobBERT oder XLM-R) liefert je einen Vektor pro Wort, darauf
sitzt pro Ebene ein linearer Kopf mit CRF.

Das Repository enthält neben der Implementierung auch das deutsche Testset: 30 Stellen-
anzeigen, 623 Sätze, unabhängig zweifach annotiert und nach dokumentierten Regeln
abgeglichen.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/prepare_data.py                              # Rohdaten -> data/processed/
python scripts/check_alignment.py --model bert-base-cased   # muss "Alignment OK" ausgeben
```

## Sanity-Check vor dem ersten echten Lauf

```bash
python scripts/train.py --config configs/bert_skill.json --smoke
```

Trainiert auf 20 Sätzen, die alle mindestens einen Span enthalten. Der Loss muss deutlich
fallen und der Dev-F1 gegen 1.0 gehen — das Modell soll diese 20 Sätze auswendig lernen.
Passiert das nicht, ist etwas in der Pipeline kaputt. Smoke-Läufe schreiben ihre Zahlen
nicht in die Ergebnistabelle der echten Experimente.

## Experimente

Alle berichteten Läufe verwenden **12 Epochen** und die drei Seeds
`3477689 4213916 8749520`. Jeder Lauf hängt eine Zeile an `results/all_runs.csv` an.

```bash
python scripts/train.py --config configs/jobbert_skill.json --seed 3477689
```

### Durchgeführte Experimente

| Experiment | Configs | Ergebnis (Ø F1 über 3 Seeds) |
|---|---|---|
| 1 — Encoder | `bert_skill` vs. `jobbert_skill` | 0.510 vs. 0.549 |
| 2 — Decoder | `jobbert_skill` vs. `jobbert_skill_linear` | 0.549 vs. 0.513 |
| 3 — Multi-Task | `jobbert_knowledge` vs. `jobbert_multi` | 0.681 vs. 0.696 (Knowledge) |
| 4 — Transfer | `xlmr_skill` auf EN- und DE-Testset | 0.535 vs. 0.351 |

Ausführliche Zahlen, Precision/Recall und Interpretation: `results/ERGEBNISSE.md`.

### Transfer ins Deutsche

Trainiert wird auf den englischen Daten, getestet auf dem deutschen Testset. Dafür liegt in
`data/processed_de/` ein zweites Datenverzeichnis: Train und Dev sind identisch mit
`data/processed/`, nur `test.jsonl` ist das deutsche Testset.

```bash
python scripts/train.py --config configs/xlmr_skill.json --seed 3477689                        # EN-Baseline
python scripts/train.py --config configs/xlmr_skill.json --data data/processed_de --seed 3477689  # Transfer
```

Im Testblock muss der Support **324** sein (SKILL-Spans im deutschen Testset), sonst wurde
auf dem englischen Testset evaluiert.

### Nicht durchgeführt

Für folgende Configs liegen keine Ergebnisse vor; sie sind als Ausgangspunkt für weitere
Ablationen vorbereitet: `jobbert_skill_crf_unconstrained`, `jobbert_skill_allsub`,
`jobbert_skill_frozen`, `jobbert_skill_len128`, `spanbert_skill`, `jobspanbert_skill`,
`bert_knowledge`, `bert_multi`, `bert_skill_linear`, `xlmr_multi`.

## Deutsches Testset reproduzieren

Die Annotation liegt als Span-Liste vor; die CoNLL- und jsonl-Dateien werden daraus erzeugt.

```bash
# Annotation A (Spans -> CoNLL, drei Varianten)
python scripts/annotate_bio.py --input data/raw_de --spans data/annotation/skill_spans.json --out data/annotation
python scripts/validate_bio.py --dir data/annotation/conll_2layer

# Inter-Annotator-Agreement zwischen Annotation A und B (vor dem Abgleich)
python scripts/iaa.py --conll data/annotation/all_jobads_2layer.conll \
    --json data/annotation/annotationen_nigina.json \
    --raw data/raw_de --dump results/abweichungen.tsv

# Einigungsfassung -> finales Testset
python scripts/merge_einigung.py --conll data/annotation/all_jobads_2layer.conll \
    --json data/annotation/annotationen_nigina.json \
    --einigung data/annotation/einigungsfassung.tsv --out data/annotation

# finales CoNLL -> Pipeline-Format
python scripts/conll_to_jsonl.py data/annotation/final_2layer.conll data/processed_de/test.jsonl
```

Kennzahlen des finalen Testsets: 324 SKILL-Spans (Ø 5,9 Tokens), 244 KNOWLEDGE-Spans
(Ø 1,6 Tokens), davon 56 innerhalb eines SKILL-Spans. Cohens κ vor dem Abgleich: 0,673
(SKILL) und 0,664 (KNOWLEDGE) auf Token-Ebene.

## Fehleranalyse

`train.py` speichert die Testvorhersagen pro Satz unter `results/predictions/`.

```bash
python scripts/fehleranalyse.py results/predictions/xlmr_skill_processed_de_seed3477689.jsonl \
    --out fehleranalyse/fehler_de
python scripts/lockerer_f1.py results/predictions/*.jsonl
```

`fehleranalyse.py` ordnet jeden Fehler einer Kategorie zu (übersehen, falscher Alarm, zu
lang, zu kurz, zersplittert, verschoben) und zieht eine Stichprobe zum Durchsehen von Hand.
`lockerer_f1.py` berechnet neben dem strikten Span-F1 eine gelockerte und eine
Token-Variante; damit lässt sich trennen, ob ein Modell Spans gar nicht findet oder nur
falsch abgrenzt.

Ergebnisse: `fehleranalyse/fehleranalyse_zahlen.md` (automatisch) und
`fehleranalyse/fehleranalyse_beispiele.md` (manuelle Einordnung).

## Abbildungen

`scripts/diagramme.py` erzeugt die Schemazeichnungen in `abbildungen/` als SVG, PDF und PNG
(Pipeline, Architektur, Subword-Alignment).

## Hyperparameter und Abweichungen vom Original

Die Configs übernehmen die Werte aus dem SkillSpan-Repo: Batch 32, AdamW mit lr 1e-4,
betas (0.9, 0.99), weight decay 0.01, Dropout 0.2, CRF mit BIO-Constraints. Bewusste
Abweichungen:

1. **Learning-Rate-Schedule.** Original: MaChAmp mit slanted triangular schedule,
   discriminative fine-tuning und gradual unfreezing. Hier: linearer Warmup (30 %) mit
   linearem Abfall.
2. **Maximale Länge.** Original: 128 Subwords mit Kürzung. Hier: 256, und lange Sätze
   werden in `prepare_data.py` an Span-Grenzen geteilt, sodass keine Spans verloren gehen.
3. **Epochen.** Original: 20. Hier: 12, aus Gründen der Rechenzeit.
4. **Seeds.** Original: fünf. Hier: drei.
5. **Eigene CRF-Implementierung** statt der AllenNLP-Variante aus MaChAmp, mit denselben
   BIO-Constraints. Der CRF läuft über die Wortfolge, nicht über die Subwords — siehe
   Bericht, Kapitel 5.
6. **Datenmenge.** Nur zwei der drei Teilmengen von SkillSpan sind veröffentlicht; die
   Zahlen sind deshalb nicht direkt mit der Tabelle im Paper vergleichbar.

Training auf der GPU ist nicht vollständig deterministisch: Läufe mit identischem Seed
können leicht abweichen (auf dem kleinen deutschen Testset bis zu vier F1-Punkte). Berichtet
werden deshalb Mittelwerte über drei Seeds.

## Aufbau

```
configs/              eine JSON-Datei pro Experiment
data/raw/             Originaldaten von github.com/kris927b/SkillSpan (MIT)
data/processed/       aufbereitete englische Daten (prepare_data.py)
data/raw_de/          30 deutsche Stellenanzeigen (Rohtext)
data/annotation/      beide Annotationen, Regeln, Einigung, finale CoNLL-Dateien
data/processed_de/    englisches Train/Dev + deutsches Testset im Pipeline-Format
scripts/              Training, Datenaufbereitung, Annotation, IAA, Fehleranalyse
src/                  data.py (Alignment), dataset.py (Batches, Evaluation), model.py
results/              all_runs.csv, ERGEBNISSE.md, Vorhersagen
fehleranalyse/        Fehlerkategorien und manuell eingeordnete Beispiele
abbildungen/          Schemazeichnungen für den Bericht
```

Details zu den englischen Daten und ihren Auffälligkeiten: `DATEN.md`.
Annotationsrichtlinien und -regeln: `data/annotation/ANNOTATION_GUIDELINES.md` und
`data/annotation/annotationsregeln.md`.

## Hinweis zur Evaluation

Gemessen wird **entity-level F1 mit seqeval**, nicht Token-Accuracy. Ein Span zählt nur als
richtig, wenn Anfang, Ende und Ebene stimmen. Token-Accuracy wäre irreführend hoch: Im
deutschen Testset gehören 94 % der Wörter zu keinem KNOWLEDGE-Span, ein Modell mit
ausschließlich `O` käme dort auf 94 % Token-Genauigkeit.

`all_runs.csv` enthält zusätzlich `test_f1_unseen_*`: F1 nur auf Test-Sätzen, die nicht
identisch im Train-Set vorkommen (812 der 3.569 englischen Test-Sätze sind Wiederholungen,
meist Boilerplate).

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

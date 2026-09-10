# Datenaufbereitung – SkillSpan

## Ordnerstruktur

```
data/raw/            Originaldaten aus github.com/kris927b/SkillSpan (MIT-Lizenz)
data/processed/      aufbereitete Daten (wird von prepare_data.py erzeugt)
  train.jsonl, dev.jsonl, test.jsonl
  labels.json        Label-Listen pro Ebene
  stats.json         Statistiken
scripts/prepare_data.py     Rohdaten -> processed
scripts/check_alignment.py  Test des Subword-Alignments mit echtem Tokenizer
src/data.py                 Laden, Alignment, Rueckrechnung auf Wort-Ebene
```

## Ausfuehren

```bash
pip install -r requirements.txt
python scripts/prepare_data.py
python scripts/check_alignment.py --model bert-base-cased
```

## Format einer Zeile in data/processed/*.jsonl

```json
{"id": "test_406", "doc_idx": 6, "source": "tech", 
 "tokens": ["deploy", "apps", "to", "Heroku", "and/or", "AWS"], 
 "skill_tags": ["B-SKILL", "I-SKILL", "O", "O", "O", "O"], 
 "knowledge_tags": ["O", "O", "O", "B-KNOWLEDGE", "O", "B-KNOWLEDGE"], 
 "seen_in_train": false}
```

`seen_in_train` gibt es nur in dev/test.

## Was bei der Aufbereitung passiert

| Schritt | Train | Dev | Test |
|---|---|---|---|
| Saetze (roh) | 4.800 | 3.174 | 3.569 |
| Ungueltige BIO-Folgen repariert (I nach O -> B) | 0 | 0 | 1 |
| Lange Saetze (>100 Woerter) geteilt | 77 -> 4.913 Stuecke | – | – |
| Skill-Spans | 2.221 | 1.070 | 1.091 |
| Knowledge-Spans | 2.969 | 1.093 | 1.174 |
| Saetze ohne Span | 3.283 | 2.260 | 2.595 |
| Identisch mit einem Train-Satz | – | 659 (13 mit Span) | 812 (52 mit Span) |

Dev und Test werden nicht gekuerzt oder gefiltert, damit die Evaluation mit dem Paper vergleichbar bleibt.

## Auffaelligkeiten im Datensatz (fuer Fehleranalyse und Bericht)

1. **Ueberlange "Saetze":** Einige Train-Eintraege haben bis zu 748 Woerter. Das sind ungeteilte
   Absaetze (z. B. Benefit-Listen). Ohne Teilung wuerden sie ueber das 512-Subword-Limit von BERT
   hinausgehen. Geteilt wird nur an Stellen, an denen kein Span unterbrochen wird.
2. **Ueberschneidung Train/Test:** 812 Test-Saetze kommen identisch im Train-Set vor, fast immer
   Boilerplate ohne Span ("Job description:", "Full-time"). Mit `seen_in_train` koennt ihr
   zusaetzlich nur auf ungesehenen Saetzen evaluieren.
3. **Inkonsistente Annotation:** 27 Test-Saetze stehen identisch im Train-Set, aber mit anderen
   Labels. Beispiel: "solving business problems through innovation and engineering practices" ist in
   Train ein langer Skill-Span, in Test ein kurzer Skill- plus ein Knowledge-Span. Das begrenzt, wie
   gut ein Modell ueberhaupt werden kann.
4. **Ueberlappende Ebenen:** In 97 Train-Saetzen gehoert ein Wort gleichzeitig zu einem Skill- und
   einem Knowledge-Span. Deshalb zwei getrennte Label-Ebenen statt eines gemeinsamen Tagsets.
5. **Steuerzeichen als Tokens:** Einige Tokens bestehen nur aus Zeichen wie `\x95`, `\x1a` oder
   `\u200d`. Tokenizer entfernen sie komplett. Alle tragen das Label O; `to_word_level()` setzt fuer
   sie O ein, es geht also kein Span verloren.
6. **Anonymisierung:** Firmennamen u. Ae. sind durch Platzhalter wie `<ORGANIZATION>` ersetzt.

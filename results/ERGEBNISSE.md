# Ergebnisse — SkillSpan-Nachimplementierung mit Transfer auf deutsche Stellenanzeigen

Stand: 21.09.2026 · 24 Trainingsläufe · alle Zahlen sind strikte Span-F1 auf dem Testset,
je 3 Seeds (3477689, 4213916, 8749520), 12 Epochen, `strategy: first`

---

## Überblick: alle Konfigurationen

| Modell | Decoder | Layer | Testset | Ø F1 | Einzelwerte |
|---|---|---|---|---|---|
| bert-base-cased | CRF | skill | EN | 0.510 | 0.5116 / 0.5177 / 0.5005 |
| JobBERT | CRF | skill | EN | 0.549 | 0.5606 / 0.5587 / 0.5289 |
| JobBERT | linear | skill | EN | 0.513 | 0.5162 / 0.5016 / 0.5197 |
| JobBERT | CRF | knowledge | EN | 0.681 | 0.6779 / 0.6815 / 0.6848 |
| JobBERT | CRF | multi (skill) | EN | 0.556 | 0.5725 / 0.5498 / 0.5462 |
| JobBERT | CRF | multi (knowledge) | EN | 0.696 | 0.6962 / 0.6881 / 0.7027 |
| XLM-R | CRF | skill | EN | 0.535 | 0.5415 / 0.5164 / 0.5483 |
| XLM-R | CRF | skill | DE (Annotation A) | 0.239 | 0.2629 / 0.2564 / 0.1977 |
| XLM-R | CRF | skill | **DE (finales Testset)** | **0.351** | 0.3511 / 0.3639 / 0.3373 |

---

## Experiment 1 — BERT vs. JobBERT

**Frage:** Bringt domänenspezifisches Pretraining auf Stellenanzeigen einen messbaren Vorteil?

| Modell | Ø F1 | Bereich |
|---|---|---|
| bert-base-cased | 0.510 | 0.5005 – 0.5177 |
| JobBERT | 0.549 | 0.5289 – 0.5606 |

**Ergebnis:** +3,9 Punkte für JobBERT. Die Wertebereiche überschneiden sich nicht
(BERT max. 0.518, JobBERT min. 0.529) — über drei Seeds ein belastbarer Unterschied.

**Einordnung:** Reproduziert die Kernaussage von SkillSpan. Domain-adaptives Pretraining
auf Stellenanzeigen hilft, obwohl JobBERT dieselbe Architektur und Größe hat wie BERT.

---

## Experiment 2 — CRF vs. linearer Klassifikationskopf

**Frage:** Lohnt ein strukturierter Decoder gegenüber unabhängiger Token-Klassifikation?

| Decoder | Ø F1 | Ø Precision | Ø Recall |
|---|---|---|---|
| CRF | 0.549 | 0.571 | 0.530 |
| linear | 0.513 | 0.515 | 0.529 |

**Ergebnis:** +3,6 Punkte für den CRF, Bereiche überschneiden sich nicht
(linear max. 0.520, CRF min. 0.529).

**Mechanismus:** Der Gewinn kommt fast vollständig über die Precision (+5,6 Punkte), der
Recall ist praktisch identisch. Der CRF erzwingt gültige BIO-Übergänge und unterdrückt
dadurch ungültige Sequenzen (`I-SKILL` ohne vorangehendes `B-SKILL`), die sonst als
fehlerhafte Teilspans gezählt würden. Bei langen Spans wirkt das stärker als bei kurzen,
weil dort mehr Übergänge pro Span stimmen müssen.

---

## Experiment 3 — Getrennte Modelle vs. Multi-Task

**Frage:** Hilft es, Skill- und Knowledge-Layer gemeinsam statt getrennt zu lernen?

| Layer | getrennt | Multi-Task | Δ |
|---|---|---|---|
| SKILL | 0.549 | 0.556 | +0,7 |
| KNOWLEDGE | 0.681 | 0.696 | +1,5 |

**Ergebnis:** Beim Knowledge-Layer überschneiden sich die Bereiche nicht
(Multi 0.688 – 0.703 gegen getrennt 0.678 – 0.685) — belastbarer Vorteil.
Beim Skill-Layer überschneiden sie sich deutlich (Multi 0.546 – 0.573 gegen getrennt
0.529 – 0.561) — hier ist es nur eine Tendenz, keine Aussage.

**Mechanismus:** Der Zugewinn beim Knowledge-Layer kommt über den Recall
(0.739 – 0.752 im Multi-Task gegen 0.706 – 0.733 getrennt). Plausibel ist, dass die
Skill-Annotation zusätzliches Signal darüber liefert, wo im Satz überhaupt fachliche
Inhalte stehen.

**Fazit:** Gemeinsames Training hilft dem einen Layer und schadet dem anderen nicht.
Das stützt die Multi-Task-Entscheidung des Papers.

### Nebenbefund: Knowledge ist deutlich leichter als Skill

Knowledge-F1 liegt durchgängig ~13 Punkte über Skill-F1. Erklärung liegt in der
Spanstruktur des Testsets:

| Layer | Ø Spanlänge | Ein-Token-Spans |
|---|---|---|
| SKILL | 6,6 Tokens | 8 % |
| KNOWLEDGE | 1,4 Tokens | 73 % |

Knowledge-Spans sind meist feste Einzelbegriffe (`Python`, `SAP`, `HGB`), Skill-Spans
lange Tätigkeitsphrasen. Bei strikter Span-Metrik, die exakte Grenzen verlangt, ist ein
Ein-Token-Span ungleich leichter zu treffen. Außerdem liegt beim Skill-Layer die
Precision über dem Recall, beim Knowledge-Layer umgekehrt — das Modell findet kurze,
wiederkehrende Ausdrücke zuverlässig, produziert dabei aber mehr Fehlalarme.

---

## Experiment 4 — XLM-R Zero-Shot-Transfer auf deutsche Stellenanzeigen

**Frage:** Wie viel Leistung geht verloren, wenn ein auf englischen Daten trainiertes
Modell ohne deutsche Trainingsdaten auf deutsche Stellenanzeigen angewendet wird?

**Aufbau:** XLM-R (xlm-roberta-base), trainiert auf englischem SkillSpan-Train/Dev,
getestet auf dem englischen Testset (1091 Spans) und auf dem finalen deutschen Testset
(324 SKILL-Spans, 30 Anzeigen). Gleiche Konfiguration, gleiche Seeds.

| Seed | Englisch | Deutsch (final) | Δ |
|---|---|---|---|
| 3477689 | 0.5415 | 0.3511 | −19,0 |
| 4213916 | 0.5164 | 0.3639 | −15,3 |
| 8749520 | 0.5483 | 0.3373 | −21,1 |
| **Ø** | **0.535** | **0.351** | **−18,5** |

**Ergebnis:** Der Sprachwechsel kostet rund 18,5 F1-Punkte. Ohne ein einziges deutsches
Trainingsbeispiel erreicht das Modell damit etwa 65 % seiner englischen Leistung.
Precision (Ø 0.372) und Recall (Ø 0.333) liegen nah beieinander; das Modell übersieht
also etwas mehr, als es falsch findet.

### Zweiter Befund — die Annotationskonvention bestimmt einen großen Teil der Zahl

Derselbe Transfer wurde zweimal gemessen: zuerst auf Annotation A (vor dem Abgleich),
dann auf dem finalen Testset. Texte, Modell und Seeds sind identisch; verändert haben
sich nur die Spangrenzen durch die Regeln R1 und R2.

| Testset | Ø F1 | Verlust gegenüber Englisch |
|---|---|---|
| Annotation A (Ø SKILL-Span 6,6 Tokens) | 0.239 | −29,6 Punkte (55 %) |
| Finales Testset (Ø SKILL-Span 5,9 Tokens) | 0.351 | −18,5 Punkte (34 %) |

Allein die Anpassung der Spangrenzen hebt die gemessene Leistung um 11,2 Punkte.
Gut ein Drittel des zunächst gemessenen Transferverlusts ging damit nicht auf die
Sprache zurück, sondern darauf, wie lang und mit welchen Rahmenwörtern die Spans
annotiert waren. Der Effekt liegt weit über der Seed-Streuung (unter 3 Punkten) und ist
damit belastbar.

**Einordnung:** Bei strikter Span-F1 ist jede Abweichung von der Konvention des
Trainingsdatensatzes ein Fehler. Das Modell hat die Grenzkonventionen von SkillSpan
gelernt (kurze Spans ohne Rahmenwörter); ein Testset mit anderer Konvention misst dann
zu einem erheblichen Teil die Konventionsabweichung und nicht die Erkennungsleistung.

### Zurückgezogene Beobachtung

Auf Annotation A war die Streuung über die Seeds auf Deutsch mehr als doppelt so groß
wie auf Englisch. Auf dem finalen Testset gilt das nicht mehr (Spanne 2,7 gegen
3,2 Punkte). Die erhöhte Instabilität war ein Artefakt der ursprünglichen Annotation
und wird nicht als Ergebnis berichtet.

### Nebenbefund

XLM-R erreicht auf Englisch 0.535 und liegt damit zwischen BERT (0.510) und JobBERT
(0.549). Das multilinguale Modell verliert gegenüber dem domänenspezifischen, aber
weniger stark als erwartet.

---

## Das deutsche Testset

30 Stellenanzeigen, selbst annotiert, zwei Layer nach SkillSpan.

| Kennzahl | Wert |
|---|---|
| Dokumente | 30 |
| Sätze | 623 |
| Tokens | 6.199 |
| SKILL-Spans (final) | 324 |
| KNOWLEDGE-Spans (final) | 244 |
| Ø Länge SKILL-Span | 5,9 Tokens |
| Ø Länge KNOWLEDGE-Span | 1,6 Tokens |
| Cohens κ vor Abgleich (Token, SKILL / KNOWLEDGE) | 0,673 / 0,664 |

Domänen: 5× Marketing/E-Commerce, 5× IT/Data/Engineering, 8× Pflege/Soziales/Pädagogik,
2× HR, je 1× Produktmanagement, Mechatronik, Verwaltung, Buchhaltung, Controlling,
Produktion, Lager, Sicherheit, Customer Service, Technisches Produktdesign.

---

## Limitationen (gehören in die Diskussion)

1. **Kleines Testset.** 30 Anzeigen, 324 SKILL-Spans. Die Streuung über drei Seeds ist
   klein, aber die Zahl der Anzeigen begrenzt, wie weit sich die Ergebnisse auf
   deutsche Stellenanzeigen insgesamt übertragen lassen.

2. **Entstehung der Annotation.** Annotation A wurde KI-gestützt erstellt, Annotation B
   manuell. Das κ misst daher die Übereinstimmung zwischen einer KI-gestützten und einer
   manuellen Annotation. Der Abgleich folgte überwiegend Annotation A (180 zu 38 bei den
   strittigen Spans); das finale Testset spiegelt vor allem deren Grenzkonventionen.

3. **Strikte Metrik.** Wie Experiment 4 zeigt, hängt die strikte Span-F1 stark an der
   Annotationskonvention. Die berichteten Werte sind deshalb als Untergrenze der
   Erkennungsleistung zu lesen; eine gelockerte Metrik (Überlappung zählt) würde
   deutlich höher liegen.

4. **Sprach- und Annotationseffekt nur teilweise getrennt.** Der Vergleich zweier
   Annotationsfassungen zeigt, dass die Konvention einen großen Anteil hat. Der
   verbleibende Verlust von 18,5 Punkten enthält aber weiterhin beide Effekte. Eine
   vollständige Trennung bräuchte ein englisches Testset, das nach denselben Regeln wie
   das deutsche annotiert ist.

5. **Nicht-deterministisches Training.** Läufe mit identischem Seed ergeben auf der GPU
   leicht unterschiedliche Trainingsverläufe (z. B. Seed 3477689, dev-F1 in Epoche 1:
   0.413 gegenüber 0.398). Das begrenzt die exakte Reproduzierbarkeit einzelner Läufe,
   nicht aber die Mittelwerte über drei Seeds.

6. **Unvollständige Vergleichsmatrix.** Für den Knowledge-Layer fehlt die
   BERT-Baseline; Experiment 1 ist nur für den Skill-Layer vollständig belegt.

---

## Reproduzierbarkeit

- Alle Läufe in `results/all_runs.csv`, Knowledge-Werte der Multi-Task-Läufe in
  `results/multi_knowledge.csv`
- Annotationen A und B, Einigung und Regeln in `data/annotation/`, Rohtexte in `data/raw_de/`
- IAA-Berechnung: `scripts/iaa.py`; Zusammenführung: `scripts/merge_einigung.py`
- Deutsches Testset (final) im Pipeline-Format: `data/processed_de/test.jsonl`
- Configs in `configs/`, Trainingsskript `scripts/train.py`
- Alle Läufe mit `epochs: 12`; frühere Läufe mit abweichendem Budget sind in
  `results/NOTES.md` vermerkt

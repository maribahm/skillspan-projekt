# Fehleranalyse an Beispielen (qualitativ)

Ergänzung zu `fehleranalyse_zahlen.md`. Die automatisch gezogenen Fehlerbeispiele
wurden manuell eingeordnet. Jede Zeile der drei TSV-Dateien hat zwei zusätzliche
Spalten: `notiz` (freie Beschreibung) und `befund` (Label zum Zählen).

Dateien:

- `fehler_de_beispiele_annotiert.tsv` – XLM-R Deutsch, 118 Zeilen
- `fehler_xlmr_en_beispiele_annotiert.tsv` – XLM-R Englisch, 144 Zeilen
- `fehler_en_beispiele_annotiert.tsv` – JobBERT Englisch, 141 Zeilen

## Verteilung der Befunde

### XLM-R Deutsch

| Kategorie | häufigster Befund | Rest |
|---|---|---|
| übersehen (30) | Substantivierung: 18 | Verbalphrase 4, Bindestrich-Ellipse 3, Soft Skill 2, sonstige 2, Artefakt 1 |
| zu kurz (30) | bricht vor Präposition ab: 15 | vor und/sowie 5, vor Komma 2, vor Genitiv 2, Verbklammer 2, sonstige 4 |
| zersplittert (30) | Adjektivreihe zerteilt, Bezugsnomen fehlt: 11 | Liste ist ein Gold-Span 7, an und/Komma 6, an Präposition 3, sonstige 3 |
| falscher Alarm (15) | plausibler Skill, Gold fehlt: 7 | Rahmen statt Inhalt 3, beginnt mit Komma 2, sonstige 3 |
| zu lang (10) | Funktionsverb links dazu: 5 | beginnt mit Komma 3, sonstige 2 |
| verschoben (3) | alle drei: Rahmen links dazu, rechts abgebrochen | |

### XLM-R Englisch

| Kategorie | häufigster Befund | Rest |
|---|---|---|
| übersehen (30) | Nominalphrase/Fachbegriff: 19 | verbal 5, Adjektiv 4, Haltung/Ziel 2 |
| falscher Alarm (30) | plausibler Skill, Gold fehlt: 14 | Firma/Angebot statt Bewerber 12, Adjektiv 4 |
| zu kurz (30) | Haltungs-/Rahmenwort links fehlt: 14 | Modifikator links 5, vor Präposition 5, nur Kern übrig 4, Artefakt 1 |
| zu lang (30) | Ergänzung rechts angehängt: 11 | über „and“ verbunden 10, Modifikator 4, über „through“ verschmolzen 4, Artefakt 1 |
| zersplittert (12) | an „and“ zerteilt: 7 | sonstige 5 |
| verschoben (12) | Aufzählung ohne Trennzeichen: 6 | Haltung weg, PP dazu 5, sonstige 1 |

### JobBERT Englisch

| Kategorie | häufigster Befund | Rest |
|---|---|---|
| übersehen (30) | nominal: 16 | verbal 6, Haltung/Ziel 5, Adjektiv 3 |
| falscher Alarm (30) | plausibler Skill, Gold fehlt: 20 | Kontext falsch 5, Adjektiv 5 |
| zu kurz (30) | Rahmen/Haltung links weg: 7 | Präposition 6, Modifikator links 5, Ergänzung rechts 4, nur Kern 4, Kopfnomen 2, Koordination 2 |
| zu lang (30) | Ergänzung rechts angehängt: 13 | Koordination über and 9, Modifikator 4, Rahmen links 2, verschmolzen 2 |
| zersplittert (16) | an „and“ zerteilt: 8 | sonstige 8 |
| verschoben (5) | Haltung weg, PP dazu: 4 | sonstige 1 |

## Bewertung der Hypothesen

**H1 (Transferverlust ist ein Abgrenzungsproblem): bestätigt, mit Einschränkung.**
Übersehen steigt von EN nach DE um 3,5 Punkte, Grenzfehler um 10. Ein Teil dieser
Grenzfehler geht aber auf unterschiedliche Annotationskonventionen zurück: Im
deutschen Testset sind ganze Soft-Skill-Listen ein Span (z. B. „Zuverlässigkeit ,
Sorgfalt , … und Teamfähigkeit“), im SkillSpan-Gold stehen koordinierte Skills
teils getrennt („Work independently and proactively“ = zwei Spans). Das Modell hat
die englische Konvention gelernt. 18 von 30 zersplitterten deutschen Fällen folgen
diesem Muster.

**H2 (Koordination im EN, Abbruch im DE): bestätigt.** Englisch: 10 von 30 zu langen
Spans entstehen durch Verbinden über „and“, gleichzeitig werden 7 von 12
zersplitterten Spans genau an „and“ getrennt. Deutsch: 15 von 30 zu kurzen Spans
brechen vor einer Präposition ab, 5 vor und/sowie, 2 vor einem Komma.

**H3 (Substantivierungen werden übersehen): Beobachtung ja, Begründung nein.**
18 von 30 übersehenen deutschen Spans sind Substantivierungen. Die Erklärung
„weil englische Anzeigen verbal formulieren“ trägt aber nicht: Auch im Englischen
sind die meisten übersehenen Spans nominal (XLM-R 19/30, JobBERT 16/30). Besser
passt: Die Substantivierung steckt in einem Rahmen, und das Modell markiert den
Rahmen statt des Inhalts (Gold „Weiterentwicklung und Optimierung des
Investitionscontrollings“ übersehen, vorhergesagt „Mitarbeit an Projekten“).

**H4 (übersehene EN-Spans sind Haltungsformulierungen): nicht haltbar in dieser Form.**
Haltungsformulierungen sind unter den übersehenen Spans die Minderheit (XLM-R 2/30,
JobBERT 5/30). Modellunabhängig ist stattdessen, dass die Haltungsrahmung bei zu
kurzen Spans abgeschnitten wird: „Show initiative“ → „initiative“, „Good at acquiring
new skills“ → „acquiring new skills“, „assist in developing …“ → „developing …“
treten bei beiden Modellen gleich auf.

## Zwei Querbefunde

**Kommas.** In keinem englischen Testsatz beider EN-Dateien steht ein Komma;
Aufzählungen erscheinen als „analytical proactive and structured workstyle“. Das
passt dazu, dass das Modell im Deutschen an Kommas abbricht, an ihnen zersplittert
und in fünf Fällen Spans sogar mit einem Komma beginnen lässt.
(Noch zu prüfen: ob das auch für die Trainingsdaten gilt.)

**Rahmenverben.** Im Englischen schneidet das Modell den Rahmen ab („enjoy“,
„ready to“, „desire to“), im Deutschen nimmt es ihn mit („kümmerst dich um das
Medikamentenmanagement“, „übernimmst die Wartung …“). Ob Rahmenverben zum Skill
gehören, beantworten die beiden Goldstandards unterschiedlich.

## Beispiele für den Bericht

Deutsch:

- Bruch vor Präposition: Gold „… sowie Wertberichtigungen nach HGB“, vorhergesagt ohne „nach HGB“.
- Bruch vor „und“: Gold „Planung der Liquidität und tägliche Überwachung der Bankkonten“, vorhergesagt nur der erste Teil.
- Listenkonvention: sechs Eigenschaften als ein Gold-Span, das Modell liefert sechs einzelne Skills.
- Adjektivreihe: „Strukturierte , sorgfältige und selbstständige Arbeitsweise“ wird in drei Adjektive zerlegt, das Bezugsnomen fällt weg.
- Rahmen statt Inhalt: „Mitarbeit an Projekten“ statt „Weiterentwicklung und Optimierung des Investitionscontrollings“.
- Funktionsverb mitgenommen: „kümmerst dich um das Medikamentenmanagement“ statt „Medikamentenmanagement“.

Englisch:

- Koordination: „critical thinking“ wird zu „analytical and critical thinking skills“.
- Gegenrichtung: Gold „coach and develop your team“ wird in zwei Spans zerlegt.
- Haltungsrahmen: „ready to face new challenges“ → „face new challenges“.
- Bedeutungsumkehr: „don't like boring repetitive tasks“ → „like boring repetitive tasks“.
- Falscher Bezug: „work with hardworking people“ beschreibt das Team, keine Anforderung.
- Annotationslücke: „elaboration of user stories“ gilt hier als falscher Alarm, in einer
  anderen Anzeige steht „Participation in the elaboration of user stories“ im Gold.

## Einschränkungen

- Stichproben pro Kategorie klein (meist 30, bei „zu lang“ DE nur 10, „verschoben“ DE nur 3);
  die Anteile gelten für die Stichprobe, nicht für alle Fehler.
- Die Einordnung stammt von einer Person bzw. einem Werkzeug; die Labelgrenzen sind teils unscharf,
  besonders zwischen „Annotationslücke“ und „Fragment“ bei falschen Alarmen.
- Eine Kontrollstichprobe von 10 englischen Fehlern wurde unabhängig eingeordnet: 8-mal identisch,
  1-mal teilweise (beidseitige Erweiterung, im EN-Schema kein eigenes Label), 1-mal abweichend
  (Abgrenzung Annotationslücke/Fragment). Daraufhin präzisiert: „Annotationslücke“, wenn der
  vorhergesagte Span allein gelesen ein verständlicher Skill wäre, sonst „Fragment“.
- Die Konventionsunterschiede zwischen dem selbst annotierten deutschen Testset und dem
  SkillSpan-Gold sind nicht systematisch erhoben, sondern an den Beispielen aufgefallen.

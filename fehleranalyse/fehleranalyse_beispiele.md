# Fehleranalyse an Beispielen

Das hier gehört zu `fehleranalyse_zahlen.md`. Die Zahlen dort sagen nur, wie viele
Fehler welcher Art auftreten, nicht warum. Deshalb habe ich mir die automatisch
gezogenen Beispiele einzeln angeschaut und jede Zeile von Hand eingeordnet. In den
drei TSV-Dateien stehen dafür zwei zusätzliche Spalten: `notiz` mit einer kurzen
Beschreibung im Klartext und `befund` mit einem Label, das sich zählen lässt.

- `fehler_de_beispiele_annotiert.tsv` – XLM-R Deutsch, 118 Zeilen
- `fehler_xlmr_en_beispiele_annotiert.tsv` – XLM-R Englisch, 144 Zeilen
- `fehler_en_beispiele_annotiert.tsv` – JobBERT Englisch, 141 Zeilen

## Was dabei herauskam

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

## Unsere vier Hypothesen im Licht der Beispiele

**H1: Der Transferverlust ist ein Abgrenzungs-, kein Erkennungsproblem.**
Das geht auf, aber mit einem Haken. Von Englisch nach Deutsch steigen die übersehenen
Spans um 3,5 Punkte, die Grenzfehler dagegen um 10. Ein Teil dieser Grenzfehler ist
allerdings hausgemacht, weil wir im deutschen Testset anders annotiert haben als
SkillSpan: Bei uns ist eine ganze Soft-Skill-Liste ein einziger Span („Zuverlässigkeit,
Sorgfalt, … und Teamfähigkeit“), im englischen Gold stehen koordinierte Skills oft
getrennt, etwa „Work independently and proactively“ als zwei Spans. Das Modell hat die
englische Variante gelernt und zieht sie im Deutschen durch – 18 der 30 zersplitterten
deutschen Fälle sehen genau so aus. Das muss man fairerweise dazusagen.

**H2: Im Englischen verbindet das Modell über „and“, im Deutschen bricht es ab.**
Passt. Im Englischen geht das sogar in beide Richtungen: 10 von 30 zu langen Spans
entstehen, weil über „and“ zusammengezogen wird, und gleichzeitig werden 7 von 12
zersplitterten Spans genau an einem „and“ auseinandergerissen. Im Deutschen brechen
15 von 30 zu kurzen Spans vor einer Präposition ab, 5 vor und/sowie, 2 vor einem Komma.

**H3: Substantivierungen werden übersehen.** Die Beobachtung stimmt, unsere Begründung
nicht. 18 der 30 übersehenen deutschen Spans sind tatsächlich Substantivierungen. Aber
die Erklärung „weil englische Anzeigen verbal formulieren“ hält nicht stand: Auch im
Englischen sind die übersehenen Spans mehrheitlich nominal (XLM-R 19/30, JobBERT 16/30).
Was besser passt: Die Substantivierung steckt meist in einem Rahmen, und das Modell
markiert den Rahmen statt des eigentlichen Inhalts. Gutes Beispiel ist „Weiterentwicklung
und Optimierung des Investitionscontrollings“, das komplett übersehen wird, während
stattdessen „Mitarbeit an Projekten“ vorhergesagt wird.

**H4: Die übersehenen englischen Spans sind Haltungsformulierungen.** Das müssen wir so
fallen lassen. Haltungsformulierungen sind unter den übersehenen Spans klar in der
Minderheit (XLM-R 2/30, JobBERT 5/30). Was dagegen bei beiden Modellen gleich auftritt:
Die Haltungsrahmung wird abgeschnitten, wenn ein Span zu kurz gerät. „Show initiative“
wird zu „initiative“, „Good at acquiring new skills“ zu „acquiring new skills“,
„assist in developing …“ zu „developing …“. Der Befund ist also da, nur an einer
anderen Stelle als gedacht.

## Strikter und lockerer F1

Für H1 wollte ich nicht nur Beispiele, sondern eine Zahl. Dafür habe ich
`scripts/lockerer_f1.py` geschrieben und auf die gespeicherten Vorhersagen losgelassen
(Seed 3477689). Strikt heißt, die Grenzen müssen exakt stimmen, das entspricht seqeval.
Locker heißt, ein Span zählt schon, wenn er sich mit einem Gold-Span überlappt. Token
bewertet ganz ohne Spangrenzen.

| | strikt | locker | Token |
|---|---|---|---|
| JobBERT EN | 0,5634 | 0,7932 | 0,7368 |
| XLM-R EN | 0,5412 | 0,7686 | 0,7109 |
| XLM-R DE | 0,3889 | 0,7975 | 0,7053 |

Die strikten Werte stimmen exakt mit unseren seqeval-Zahlen überein, das Skript rechnet
also richtig. Und dann passiert das Interessante: Der Abstand von 15 Punkten zwischen
Englisch und Deutsch verschwindet beim lockeren F1 vollständig, Deutsch liegt sogar
minimal darüber. Die lockere Precision im Deutschen ist 0,948 – fast jede Vorhersage
trifft irgendwo einen echten Skill, das Modell rät also nicht wild herum. Der lockere
Recall liegt bei 0,688 gegenüber 0,723 im Englischen, das ist ein kleiner Unterschied.
Damit ist H1 für mich belegt: Das Modell findet die Stellen, es schneidet sie nur falsch zu.

Wichtig für den Bericht: Der strikte F1 bleibt unsere Hauptmetrik, so wie in SkillSpan.
Die anderen beiden sind reine Diagnose und sollen das Ergebnis nicht schönrechnen.

## Zwei Sachen, die mir nebenbei aufgefallen sind

**Kommas.** In den englischen Testdaten stehen ganze 3 Kommas auf 3569 Zeilen, im
deutschen Testset 274 auf 623 Zeilen. Aufzählungen sehen im Englischen aus wie
„analytical proactive and structured workstyle“. Das Modell hat Kommas also praktisch
nie gesehen und stolpert im Deutschen dauernd darüber: Es bricht an ihnen ab,
zersplittert an ihnen, und in fünf Fällen fängt ein vorhergesagter Span sogar mit einem
Komma an. Ob das für die Trainingsdaten genauso gilt, habe ich noch nicht geprüft.

**Rahmenverben.** Im Englischen wirft das Modell den Rahmen weg („enjoy“, „ready to“,
„desire to“), im Deutschen nimmt es ihn mit („kümmerst dich um das Medikamentenmanagement“,
„übernimmst die Wartung …“). Ehrlich gesagt beantworten die beiden Goldstandards die
Frage, ob so ein Rahmenverb zum Skill gehört, selbst unterschiedlich. Das ist also nicht
nur ein Modellproblem.

## Beispiele, die wir im Bericht zeigen können

Deutsch:

- Bruch vor Präposition: Gold „… sowie Wertberichtigungen nach HGB“, vorhergesagt ohne „nach HGB“.
- Bruch vor „und“: Gold „Planung der Liquidität und tägliche Überwachung der Bankkonten“, vorhergesagt nur der erste Teil.
- Unsere Listenkonvention: sechs Eigenschaften sind ein Gold-Span, das Modell liefert sechs einzelne Skills.
- Adjektivreihe: „Strukturierte, sorgfältige und selbstständige Arbeitsweise“ wird in drei Adjektive zerlegt, das Bezugsnomen fällt hinten runter.
- Rahmen statt Inhalt: „Mitarbeit an Projekten“ statt „Weiterentwicklung und Optimierung des Investitionscontrollings“.
- Funktionsverb mitgenommen: „kümmerst dich um das Medikamentenmanagement“ statt nur „Medikamentenmanagement“.

Englisch:

- Koordination: aus „critical thinking“ wird „analytical and critical thinking skills“.
- Und andersherum: Gold „coach and develop your team“ wird in zwei Spans zerlegt.
- Haltungsrahmen weg: „ready to face new challenges“ → „face new challenges“.
- Bedeutungsumkehr, mein Lieblingsfall: „don't like boring repetitive tasks“ → „like boring repetitive tasks“.
- Falscher Bezug: „work with hardworking people“ beschreibt das Team, ist also gar keine Anforderung an Bewerber.
- Annotationslücke: „elaboration of user stories“ zählt hier als falscher Alarm, in einer anderen Anzeige steht „Participation in the elaboration of user stories“ aber im Gold.

## Was man dazu sagen muss

Die Stichproben sind klein, meist 30 pro Kategorie, bei „zu lang“ im Deutschen nur 10
und bei „verschoben“ sogar nur 3. Die Anteile oben gelten für die Stichprobe und nicht
automatisch für alle Fehler.

Die Einordnung kommt von einer Person, und manche Labelgrenzen sind unscharf, vor allem
zwischen „Annotationslücke“ und „Fragment“ bei den falschen Alarmen. Um das zu prüfen,
haben wir 10 englische Fehler ein zweites Mal unabhängig eingeordnet: 8-mal kam dasselbe
heraus, 1-mal teilweise (beidseitige Erweiterung, dafür gibt es im englischen Schema kein
eigenes Label) und 1-mal etwas anderes, genau an der Grenze Annotationslücke/Fragment.
Daraufhin haben wir die Regel geschärft: Annotationslücke, wenn der vorhergesagte Span
für sich allein gelesen ein verständlicher Skill wäre, sonst Fragment.

Und die Unterschiede zwischen unserem deutschen Testset und dem SkillSpan-Gold sind uns
an den Beispielen aufgefallen, wir haben sie nicht systematisch erhoben. Das wäre ein
eigener Arbeitsschritt.

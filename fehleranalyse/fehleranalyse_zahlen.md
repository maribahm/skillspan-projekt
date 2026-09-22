# Fehleranalyse – automatische Einordnung (Seed 3477689)

Grundlage: je ein Lauf mit gespeicherten Vorhersagen.
JobBERT Englisch F1 0.5634 · XLM-R Englisch F1 0.5412 · XLM-R Deutsch F1 0.3889.
Einordnung aus Sicht der Gold-Spans; falsche Alarme als Anteil der Vorhersagen.
Erzeugt mit `scripts/fehleranalyse.py`, Werte stimmen exakt mit seqeval überein.

## Verteilung der Fehler

| | JobBERT EN | XLM-R EN | XLM-R DE |
|---|---|---|---|
| Gold-Spans | 1091 | 1091 | 324 |
| exakt getroffen | 53,3 % | 50,2 % | 36,7 % |
| übersehen | 24,3 % | 27,7 % | 31,2 % |
| Grenzfehler gesamt | 22,4 % | 22,1 % | 32,1 % |
| – zu lang | 12,3 % | 13,6 % | 3,1 % |
| – zu kurz | 8,2 % | 6,3 % | 17,3 % |
| – zersplittert | 1,5 % | 1,1 % | 10,8 % |
| – verschoben | 0,5 % | 1,1 % | 0,9 % |
| falsche Alarme (von den Vorhersagen) | 16,7 % | 18,0 % | 5,2 % |

## Exakte Treffer nach Länge des Gold-Spans

| Länge | JobBERT EN | XLM-R EN | XLM-R DE |
|---|---|---|---|
| 1 Token | 44,3 % | 47,8 % | 48,0 % |
| 2–3 Tokens | 55,5 % | 49,6 % | 38,3 % |
| 4–6 Tokens | 58,1 % | 52,4 % | 34,8 % |
| 7+ Tokens | 48,4 % | 49,7 % | 33,3 % |

Übersehen nach Länge, XLM-R DE: 50,0 % / 48,9 % / 34,8 % / 15,9 %
Grenzfehler nach Länge, XLM-R DE: 2,0 % / 12,8 % / 30,3 % / 50,7 %

## Häufigste Tokens an falschen Grenzen

- JobBERT EN, zu lang: zusätzliches „and“ 62-mal (24 links, 38 rechts)
- XLM-R EN, zu lang: zusätzliches „and“ 68-mal (20 links, 48 rechts)
- XLM-R DE, zu kurz, fehlend rechts: „und“ 27, Komma 12, „in“ 10, „der“ 9, „im“ 5, „zur“ 4, „für“ 4

## Häufigste erste Tokens übersehener Spans

- JobBERT EN: work, achieve, teaching, stay, development, research, build, code
- XLM-R EN: work, achieve, stay, teaching, development, research, build, working
- XLM-R DE: sicherer, weiterentwicklung, zusammenarbeit, dokumentation, enge, unterrichten, vermittlung

## Hypothesen zum Prüfen an den Beispielen (nicht belegt)

1. Der Transferverlust ist vor allem ein Abgrenzungsproblem, kein Erkennungsproblem.
2. Im Englischen verbindet das Modell koordinierte Skills über „and“, im Deutschen
   bricht es lange Nominalphrasen an „und“, Kommas und Präpositionen ab.
3. Kurze deutsche Spans im Nominalstil (Substantivierungen) werden übersehen, weil
   englische Anzeigen Tätigkeiten eher mit Verben ausdrücken.
4. Die im Englischen übersehenen Spans sind modellunabhängig ähnlich: Haltungs- und
   Zielformulierungen („work independently“, „achieve goals“, „stay up to date“).

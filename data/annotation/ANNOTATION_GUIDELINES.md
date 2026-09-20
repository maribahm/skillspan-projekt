# Annotationsrichtlinien — Skill-Extraktion aus deutschen Stellenanzeigen (v2)

Stand: 18.09.2026 · 30 Anzeigen · 623 Sätze · 6.199 Tokens
SKILL: 284 Spans · KNOWLEDGE: 227 Spans (v3, nach Abgleich mit der externen Review)

## 1. Zwei Layer statt einem

v1 hatte ein einziges Label `SKILL` und warf Werkzeuge, Sprachen und Fähigkeiten
zusammen. Das passt nicht zu SkillSpan (Zhang et al., NAACL 2022) und nicht zu Modellen,
die mit `layers=skill` trainiert wurden: `Python` oder `Google Ads` gehören dort in den
Knowledge-Layer, ein Skill-Modell kann sie gar nicht finden. v2 trennt deshalb:

| Layer | Inhalt | Beispiele |
|---|---|---|
| `SKILL` | Fähigkeit oder Tätigkeit, meist verbale oder nominalisierte Phrase | `Betreuung von Windows Arbeitsplätzen und Endgeräten`, `Selbstständige, strukturierte Arbeitsweise` |
| `KNOWLEDGE` | Werkzeug, Technologie, Fachdomäne, Sprache | `Python`, `SAP PS`, `HGB`, `Arbeitsrecht`, `Deutsch` |

Die Layer sind **unabhängig**: ein KNOWLEDGE-Span darf in einem SKILL-Span liegen.
53 der 221 KNOWLEDGE-Spans (24 %) sind so eingebettet, z. B.
`[Programmierung mit [Python]_K]_S`. Innerhalb eines Layers überlappen Spans nie.

## 2. Ausgabevarianten

| Datei / Ordner | Spalten | Zweck |
|---|---|---|
| `conll_skill/`, `all_jobads_skill.conll` | Token + SKILL | Modelle mit `layers=skill` |
| `conll_knowledge/`, `all_jobads_knowledge.conll` | Token + KNOWLEDGE | Modelle mit `layers=knowledge` |
| `conll_2layer/`, `all_jobads_2layer.conll` | Token + SKILL + KNOWLEDGE | Multi-Task-Modell |

Ein einspaltiges BIO-Format kann die Verschachtelung nicht abbilden — genau deshalb
arbeitet SkillSpan mit zwei Layern, und genau deshalb gibt es hier drei Dateien statt einer.

## 3. Spangrenzen im SKILL-Layer

Annotiert wird die **ganze Tätigkeitsphrase**, nicht das Kopfnomen allein:

- richtig: `Betreuung, Optimierung und Performance-Analyse der Websites und Social-Media-Kanäle`
- falsch (v1): `Performance-Analyse`

Konkret heisst das:

1. **Verb-geführte Phrasen werden mitannotiert**, wenn die Anzeige so formuliert ist:
   `programmierst und konfigurierst Steuerungen und Software`,
   `stellen eine hohe Datenqualität und Datenverfügbarkeit sicher`.
2. **Objekt und präpositionale Ergänzung gehören dazu**:
   `Dokumentation aller Vorgänge im Ticketsystem`, nicht nur `Dokumentation`.
3. **Rahmenwörter bleiben draussen**: `Erfahrung in`, `Kenntnisse in`, `Sehr gute`,
   `Fundierte`. Ausnahme: wenn das Rahmenwort selbst die Fähigkeit benennt
   (`Sicherer Umgang mit gängigen SEO- und Analyse-Tools`).
4. **Prädikative und adjektivische Soft Skills werden jetzt annotiert** — Änderung
   gegenüber v1: `handwerklich geschickt, lösungsorientiert und zuverlässig`,
   `kommunikations- und überzeugungsfähig`, `zuverlässig, flexibel und teamfähig`.
5. **Koordinierte Aufzählungen mit gemeinsamem Rahmen bleiben ein Span**:
   `Zuverlässigkeit, Sorgfalt, Verantwortungsbewusstsein, Flexibilität, Belastbarkeit und
   Teamfähigkeit`. Stehen die Punkte als eigene Listenzeilen, sind es eigene Spans.

Ergebnis: Ø 6,5 Tokens pro SKILL-Span, nur 9 % Ein-Token-Spans (v1: 60 %).
KNOWLEDGE-Spans sind dagegen naturgemäss kurz (Ø 1,4 Tokens, 72 % ein Token) — ein
Produktname ist ein Produktname.

## 4. Was nicht annotiert wird

- **Jobtitel und Rollen**: `Performance Marketing Manager`, `Product Owner`. Kopfzeilen
  sind über `skip_lines` komplett ausgenommen.
- **Formale Qualifikationen**: `abgeschlossenes Studium im Bereich Informatik`,
  `Ausbildung zum Fachinformatiker`. Auch die Fachrichtung darin bleibt `O` — deshalb ist
  `Energietechnik` in Anzeige 30 Zeile 10 (Studienfach) nicht annotiert, in Zeile 13
  (geforderte Kenntnis) dagegen KNOWLEDGE.
- **Zertifikate, Lizenzen, behördliche Unterrichtungen**: `A-CSPO`, `Führerschein der
  Klasse B`, `Staplerschein`, `Unterrichtung nach § 34a GewO`.
- **Bereitschafts- und Verfügbarkeitsaussagen**: `Bereitschaft zum Schichtdienst`,
  `Bereitschaft zu Dienstreisen`, `Reisetätigkeit`.
- **Erfahrungsdauer und Niveaustufen**: `mindestens zwei Jahre`, `C1`, `B2`.
- **Benefits und Selbstbeschreibung des Unternehmens**.

## 5. Statistik

| Kennzahl | SKILL | KNOWLEDGE |
|---|---|---|
| Spans | 284 | 227 |
| Span-Tokens | 1.871 (30,2 %) | 327 (5,3 %) |
| Ein-Token-Spans | 24 (8 %) | 165 (73 %) |
| Ø Spanlänge | 6,6 Tokens | 1,4 Tokens |

30 Anzeigen, 623 Sätze, 6.199 Tokens. Domänen: 5× Marketing/E-Commerce,
5× IT/Data/Engineering, 8× Pflege/Soziales/Pädagogik, 2× HR, je 1× Produktmanagement,
Mechatronik, Verwaltung, Buchhaltung, Controlling, Produktion, Lager, Sicherheit,
Customer Service, Technisches Produktdesign.

## 6. Offene Punkte für die Doppelannotation

1. **Spanlänge im SKILL-Layer.** 6,5 Tokens im Schnitt ist eher länger als bei SkillSpan.
   Strittig sind vor allem Aufzählungen: ein langer Span über die ganze Aufzählung oder
   mehrere kurze? Hier: ein Span, wenn ein gemeinsamer Rahmen da ist.
2. **Tätigkeit vs. Domäne.** `Kundenservice` (Anzeige 03) steht als Lerninhalt und ist
   KNOWLEDGE; `Kundensupport und technische Beratung` (Anzeige 13) ist eine Tätigkeit und
   SKILL. Dieselbe Sache, zwei Layer — der häufigste Streitfall.
3. **Sprachen.** Hier durchgehend KNOWLEDGE (`Deutsch`, `Englischkenntnisse`), auch wenn
   der Satz eine Fähigkeit beschreibt; die umgebende Phrase ist dann zusätzlich SKILL.
4. **Aufgabentext vs. Anforderungstext.** Beide werden annotiert.

Für Cohens κ auf Span-Ebene lohnt sich die Unterscheidung strikt / gelockert: strikt
verlangt identische Grenzen, gelockert wertet Überlappung als Treffer. Bei langen
SKILL-Spans fällt der strikte Wert erfahrungsgemäss deutlich ab, und genau dieser
Unterschied gehört in den Bericht.


## 7. Korrekturen in v3 (Abgleich mit externer Review)

1. `Produktmanagement` in Anzeige 04, Zeile 21 ist ein Abteilungsname ("Abläufe zwischen
   Produktmanagement, Entwicklung, Produktion") und wird nicht mehr annotiert. Die Nennung
   in Zeile 26 ("Erfahrung im Produktmanagement") bleibt KNOWLEDGE.
2. `Backup`, `Recovery-Lösungen` (Anzeige 13) und `Marketing- und Analyseplattformen`
   (Anzeige 01) sind jetzt zusätzlich KNOWLEDGE — sie standen vorher nur im umgebenden
   SKILL-Span, obwohl das gleichrangige `Firewall` bzw. `SEO- und Analyse-Tools` als
   KNOWLEDGE geführt wurde.
3. In den Themenlisten der Trainer-Anzeigen (02, 03) sind jetzt alle Einträge KNOWLEDGE,
   auch `Kundengewinnung` und `Projektarbeit`. Vorher waren einzelne Einträge SKILL,
   obwohl sie in derselben Aufzählung stehen.
4. Anzeige 26, Zeile 8 ("wirken Sie bei HR-Projekten mit") war nicht abgedeckt und ist
   jetzt SKILL.

Bewusst **nicht** übernommen:

- Die kurzen Spangrenzen der Review (Flag `Grenze`, 45 Fälle). 44 davon stecken hier in
  einem längeren SKILL-Span, was das dort notierte Problem ("Handlung steht außerhalb des
  Spans") auflöst. Der 45. Fall, `Business Cases` in Anzeige 04 Zeile 9, ist eine reine
  Nennung ohne Tätigkeit und bleibt nur KNOWLEDGE.
- 36 Umsortierungen von KNOWLEDGE nach SKILL bei Fachgebietsnomen
  (`Suchmaschinenoptimierung`, `Data Engineering`, `CI/CD-Pipelines`, `Controlling` …).
  Regel hier: benennt das Nomen ein Fachgebiet oder ein Werkzeug, ist es KNOWLEDGE; die
  Tätigkeit steckt im umgebenden Verb und wird als eigener SKILL-Span erfasst.
- `Fachkenntnisse` (Anzeige 17): zu unspezifisch, benennt keine Kompetenz.
- `Fließende Deutschkenntnisse`: hier nur `Deutschkenntnisse`, damit Sprachangaben über
  alle 30 Anzeigen dieselbe Grenze haben.

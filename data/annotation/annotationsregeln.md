# Annotationsregeln – Ergänzung zu den SkillSpan-Guidelines (deutsche Stellenanzeigen)

Grundlage: Zhang et al. (2022), Appendix B. Verweise in Klammern beziehen sich auf die dortigen Abschnitte. Die Regeln wurden aus den 467 Abweichungen zwischen Annotation A und B abgeleitet; R1–R3 erklären 456 davon.

## R1 – Rahmenwörter: raus, außer sie sind der einzige Kopf

Nicht in den Span gehören (B.3.6, B.3.7, B.1.1):

- Grad und Füllwörter: *Sehr gute, Gute, Hohes Maß an, ausgeprägte, stabiles, sicherer, fließende, verhandlungssichere, in Wort und Schrift*
- Auslöser: *Fähigkeit, Kenntnisse in, Fundiertes Verständnis für, Fachwissen, Grundlagen des, Praxis im, Interesse an*
- Beteiligungsrahmen: *Unterstützung bei, Mitarbeit an/bei, Mitwirkung an, wirken mit, Verantwortung für, verantworten*
- Leere Verben: *übernimmst, kümmerst dich um, sorgen für*; bei *Umgang mit, Einsatz, arbeiten mit* wird **nur** das Wissensobjekt als KNOWLEDGE markiert (B.2.4), kein SKILL
- Personalpronomen am Span-Rand: *Du, Sie*
- Häufigkeit: *tägliche, monatliche*
- Firmen-spezifischer Anhang: *für deutsche Gesellschaften, unserer Kunden (Server, …), am Standort Harburg, in enger Zusammenarbeit mit …, für digitale und gedruckte Formate* (B.1.3, B.3.5)
- Beispielklammern: *( z . B . Körperpflege , … )* – die Elemente werden, falls relevant, eigene Spans

Bleibt im Span:

- Der Rahmen, wenn danach keine eigene Tätigkeit folgt: *Mitwirkung an Produktstrategie , Roadmaps und Business Cases*, *Unterstützung bei technischen Anfragen*
- Art und Weise (B.1.6): *Eigenständige, Eigenverantwortliche, souverän, sorgfältig und nachvollziehbar*
- Fachlicher Zusatz, der den Inhalt bestimmt: *nach HGB*, *für Investitionsprojekte*
- Abkürzungsklammern (B.1.5): *Künstliche Intelligenz ( KI )*, *( MV/HV )*
- Tokengrenzen gehen vor: *Deutschkenntnisse* bleibt ganz; ein Pronomen mitten im Span (*übersetzen Sie fachliche …*) bleibt stehen

## R2 – Koordination: trennen, außer bei gemeinsamem Kopf

- Getrennt, wenn jedes Glied eigenen Kopf hat (B.1.2): *Prüfung von Steuerbescheiden* | *Sicherstellung termingerechter Vorauszahlungen*
- Getrennt bei Soft-Skill-Listen ohne Verb (B.1.2.3): *Teamfähigkeit* | *Kreativität* | …, *zuverlässig* | *flexibel* | *teamfähig*
- Getrennt bei KNOWLEDGE-Listen (B.2.8): *Logistik* | *Fulfillment*
- **Ein** Span bei gemeinsamem Argument (B.1.2.1): *Planung , Überwachung und Einhaltung des Marketingbudgets*, *Durchführung der allgemeinen Grundpflege und Behandlungspflege*
- **Ein** Span bei Ergänzungsstrich (B.2.7, deutsche Entsprechung von "application, data and infrastructure architecture"): *Kommunikations - und Teamfähigkeit*, *Data-Warehouse - oder Lakehouse-Architekturen*, *Deutsch - und Englischkenntnisse*
- Anaphorische Anschlüsse fallen weg (B.1.2.2): *… und baust sie zusammen* bleibt nur, wo beide schon einig waren; *betreust diese …*, *– und testest sie …* entfallen

## R3 – KNOWLEDGE: was man besitzt, nicht was man bearbeitet

KNOWLEDGE ist (B.2.1, B.3.13):

- benannte Tools, Technologien, Normen: *DATEV, Kubernetes, HGB, SAP PS*
- Fachgebiete und Disziplinen: *Content Marketing, Investitionscontrolling, politische Bildung, sozialrechtliche Fragestellungen*
- Branchen und Arbeitsfelder: *B2B-Umfeld, Hotellerie - , Tourismus - oder Lifestyle-Branche, Krippen - oder Elementarbereich*
- Sprachen: *Deutschkenntnisse, Englisch*

Kein KNOWLEDGE:

- Arbeitsgegenstände: *Website, Marketingbudgets, Backlinks, KPIs, Datenlandschaft, Generatoren*
- Tätigkeiten – die sind SKILL: *Grundpflege, Medikamentenmanagement, Montage - oder Inbetriebnahmetätigkeiten, Reporting*
- Unterbestimmtes (B.2.5): *Software, Hardware, IT-Systeme, Normen, Qualitätsstandards, Fremdsprachen, EDV-Kenntnisse*
- Firmen, Organisationen, Abteilungen: *Marriott-Umfeld, Destatis*
- Formale Abschlüsse, Zertifikate, Lizenzen: *abgeschlossenes Studium, Staplerschein, Führerschein Klasse B* – werden nach den Annotationsrichtlinien (Abschnitt 4) gar nicht annotiert

Prüffrage: Würde man es im Lebenslauf unter "Kenntnisse" aufführen? Im Zweifel SKILL (B.3.1).

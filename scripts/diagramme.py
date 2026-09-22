#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diagramme.py -- erzeugt die drei Schemadiagramme fuer Abschnitt 3 des Berichts.

  abb1_pipeline      Vom Satz zum BIO-Tag
  abb2_architektur   Gemeinsamer Encoder, zwei Koepfe mit je eigenem CRF
  abb3_alignment     Subword-Alignment und warum der CRF ueber Woerter laufen muss

Ausgabe jeweils als SVG (fuer Word/LaTeX skalierbar) und PDF.
Farben: Okabe-Ito-Palette, fuer Farbenblindheit und Schwarzweissdruck geeignet.

Die Subword-Zerlegung in Abb. 1 und 3 ist SCHEMATISCH. Vor der Abgabe durch die echte
Tokenizer-Ausgabe ersetzen (siehe Hinweis am Ende der Datei).
"""

import cairosvg

FONT = "Helvetica, Arial, 'DejaVu Sans', sans-serif"
INK = "#1f2328"       # Linien und Text
MUTED = "#6b7280"     # Nebentext
LINE = "#9aa1ab"      # duenne Rahmen
FILL = "#f3f5f8"      # neutrale Flaeche
SKILL = "#0072B2"     # Okabe-Ito blau
KNOW = "#E69F00"      # Okabe-Ito orange
BAD = "#C0392B"       # ungueltiger Uebergang

# ------------------------------------------------------------------ Grundbausteine

def svg(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" font-family="{FONT}">\n'
            f'<defs><marker id="pfeil" viewBox="0 0 10 10" refX="9" refY="5" '
            f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker></defs>\n'
            f'<rect width="{w}" height="{h}" fill="white"/>\n{body}</svg>\n')


def box(x, y, w, h, fill=FILL, stroke=LINE, sw=1.2, rx=6, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>\n')


def text(x, y, s, size=14, anchor="middle", weight="normal", color=INK, style="normal"):
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" '
            f'font-weight="{weight}" font-style="{style}" fill="{color}">{s}</text>\n')


def arrow(x1, y1, x2, y2, color=INK, sw=1.4):
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" marker-end="url(#pfeil)"/>\n')


def tag(x, y, label, w=64, h=26):
    """BIO-Tag als farbige Marke."""
    if label.endswith("SKILL"):
        fill, stroke, col = "#e6f1f8", SKILL, SKILL
    elif label.endswith("KNOW"):
        fill, stroke, col = "#fdf3e0", KNOW, "#8a5a00"
    elif label == "–":
        fill, stroke, col = "white", LINE, MUTED
    else:
        fill, stroke, col = "white", LINE, INK
    out = box(x - w / 2, y - h / 2, w, h, fill=fill, stroke=stroke, rx=4,
              dash="3 3" if label == "–" else None)
    out += text(x, y + 5, label.replace("KNOW", "KNOWL."), size=12, color=col,
                weight="bold" if label[0] in "BI" else "normal")
    return out


# ------------------------------------------------------------------ Abb. 1 Pipeline

def abb1():
    W, H = 1100, 330
    b = ""
    stages = [
        ("Satz", ["Programmierung", "mit Python"]),
        ("Wörter", ["Programmierung", "mit", "Python"]),
        ("Subwords", ["Program ##mier", "##ung", "mit Python"]),
        ("Encoder", ["XLM-R / JobBERT", "ein Vektor", "pro Subword"]),
        ("Erstes Subword", ["ein Vektor", "pro Wort"]),
        ("CRF je Layer", ["Viterbi mit", "BIO-Constraints"]),
    ]
    bw, bh, gap, x0, y0 = 150, 118, 30, 30, 50
    for i, (title, lines) in enumerate(stages):
        x = x0 + i * (bw + gap)
        b += box(x, y0, bw, bh)
        b += text(x + bw / 2, y0 + 26, title, size=15, weight="bold")
        for k, ln in enumerate(lines):
            b += text(x + bw / 2, y0 + 56 + k * 20, ln, size=12.5, color=MUTED)
        if i < len(stages) - 1:
            b += arrow(x + bw + 3, y0 + bh / 2, x + bw + gap - 3, y0 + bh / 2)

    # Ausgabe unten: je ein Tag pro Wort und Layer
    oy = 225
    b += text(x0, oy - 18, "Ausgabe: je Layer ein Tag pro Wort", size=14, anchor="start",
              weight="bold")
    words = ["Programmierung", "mit", "Python"]
    sk = ["B-SKILL", "I-SKILL", "I-SKILL"]
    kn = ["O", "O", "B-KNOW"]
    cx0 = x0 + 240
    b += text(x0, oy + 28, "SKILL", size=13, anchor="start", color=SKILL, weight="bold")
    b += text(x0, oy + 62, "KNOWLEDGE", size=13, anchor="start", color="#8a5a00", weight="bold")
    for j, w in enumerate(words):
        cx = cx0 + j * 150
        b += text(cx, oy, w, size=13)
        b += tag(cx, oy + 23, sk[j], w=96)
        b += tag(cx, oy + 57, kn[j], w=96)
    b += text(cx0 + 2 * 150 + 75, oy + 28, "→  Span: Programmierung mit Python",
              size=13, anchor="start", color=SKILL)
    b += text(cx0 + 2 * 150 + 75, oy + 62, "→  Span: Python",
              size=13, anchor="start", color="#8a5a00")
    b += text(W - 30, H - 12, "Subword-Zerlegung schematisch", size=11, anchor="end",
              color=MUTED, style="italic")
    return svg(W, H, b)


# ------------------------------------------------------------------ Abb. 2 Architektur

def abb2():
    W, H = 760, 560
    b = ""
    cx = W / 2
    # Eingabe
    toks = ["Program", "##mier", "##ung", "mit", "Python"]
    tw = 104
    tx0 = cx - len(toks) * tw / 2
    for i, t in enumerate(toks):
        b += box(tx0 + i * tw + 4, 492, tw - 8, 34, fill="white")
        b += text(tx0 + i * tw + tw / 2, 514, t, size=13)
    b += text(tx0 - 14, 514, "Subwords", size=13, anchor="end", color=MUTED)
    b += arrow(cx, 488, cx, 442)

    # Encoder
    b += box(cx - 260, 360, 520, 80, fill="#eceff3", stroke=INK, sw=1.4)
    b += text(cx, 395, "Vortrainierter Encoder", size=16, weight="bold")
    b += text(cx, 418, "BERT · JobBERT · XLM-R — gemeinsam für beide Layer", size=13,
              color=MUTED)
    b += arrow(cx, 358, cx, 318)

    # Auswahl erstes Subword
    b += box(cx - 200, 272, 400, 44, fill="white")
    b += text(cx, 299, "Erstes Subword je Wort (Folge-Subwords ignoriert)", size=13)

    # zwei Koepfe
    for side, (name, col, fill, lab) in enumerate([
            ("SKILL", SKILL, "#e6f1f8", "Tags SKILL"),
            ("KNOWLEDGE", KNOW, "#fdf3e0", "Tags KNOWLEDGE")]):
        hx = cx - 170 if side == 0 else cx + 170
        b += f'<path d="M{cx},{270} L{cx},{252} L{hx},{252} L{hx},{232}" fill="none" ' \
             f'stroke="{INK}" stroke-width="1.4" marker-end="url(#pfeil)"/>\n'
        b += box(hx - 110, 186, 220, 44, fill=fill, stroke=col, sw=1.6)
        b += text(hx, 213, f"Linearer Kopf {name}", size=13.5, weight="bold",
                  color=col if side == 0 else "#8a5a00")
        b += arrow(hx, 184, hx, 156)
        b += box(hx - 110, 110, 220, 44, fill=fill, stroke=col, sw=1.6)
        b += text(hx, 137, f"CRF {name}", size=13.5, weight="bold",
                  color=col if side == 0 else "#8a5a00")
        b += arrow(hx, 108, hx, 80)
        b += text(hx, 70, lab, size=13.5)
        b += text(hx, 50, "B · I · O", size=12.5, color=MUTED)

    b += text(cx, 26, "Loss = Loss SKILL + Loss KNOWLEDGE (Multi-Task)", size=13,
              color=MUTED, style="italic")
    return svg(W, H, b)


# ------------------------------------------------------------------ Abb. 3 Alignment

def abb3():
    W, H = 1040, 490
    b = ""
    words = [("Programmierung", 3), ("mit", 1), ("Python", 1)]
    subs = ["Program", "##mier", "##ung", "mit", "Python"]
    sw_ = 118
    x0 = 170

    def row_label(y, s):
        return text(x0 - 20, y, s, size=13, anchor="end", color=MUTED)

    # Wortzeile
    b += row_label(56, "Wörter")
    k = 0
    for w, n in words:
        b += box(x0 + k * sw_ + 4, 34, n * sw_ - 8, 34, fill=FILL)
        b += text(x0 + (k + n / 2) * sw_, 56, w, size=14, weight="bold")
        k += n
    # Subwordzeile
    b += row_label(114, "Subwords")
    for i, s in enumerate(subs):
        b += box(x0 + i * sw_ + 6, 94, sw_ - 12, 32, fill="white")
        b += text(x0 + (i + 0.5) * sw_, 115, s, size=13)
    # Goldlabel pro Wort
    b += row_label(164, "Label pro Wort")
    gold = ["B-SKILL", "–", "–", "I-SKILL", "I-SKILL"]
    for i, g in enumerate(gold):
        b += tag(x0 + (i + 0.5) * sw_, 160, g, w=96)
    b += text(x0 + 5 * sw_ + 16, 165, "Folge-Subwords: kein Label (maskiert)",
              size=12.5, anchor="start", color=MUTED)

    # Panel a: falsch
    ya = 280
    b += text(40, ya - 66, "(a) CRF über Subwords, Maskierte als O gezählt", size=14,
              anchor="start", weight="bold")
    wrong = ["B-SKILL", "O", "O", "I-SKILL", "I-SKILL"]
    for i, g in enumerate(wrong):
        b += tag(x0 + (i + 0.5) * sw_, ya + 10, g, w=96)
    # ungueltiger Uebergang O -> I markieren: Bogen von Box-Mitte zu Box-Mitte
    xa = x0 + 2.5 * sw_
    xb = x0 + 3.5 * sw_
    b += f'<path d="M{xa},{ya-4} C{xa},{ya-40} {xb},{ya-40} {xb},{ya-8}" ' \
         f'fill="none" stroke="{BAD}" stroke-width="2" marker-end="url(#pfeil)"/>\n'
    b += text((xa + xb) / 2, ya - 38, "O → I ungültig", size=12.5, color=BAD, weight="bold")
    b += text(x0 + 5 * sw_ + 16, ya + 6, "Gold-Folge verletzt BIO,", size=12.5,
              anchor="start", color=BAD)
    b += text(x0 + 5 * sw_ + 16, ya + 24, "Loss explodiert (> 16.000)", size=12.5,
              anchor="start", color=BAD)

    # Panel b: richtig
    yb = 400
    b += text(40, yb - 30, "(b) CRF über die lückenlose Wortfolge", size=14,
              anchor="start", weight="bold")
    right = [("B-SKILL", 1), ("I-SKILL", 3), ("I-SKILL", 4)]
    pos = [x0 + 0.5 * sw_, x0 + 3.5 * sw_, x0 + 4.5 * sw_]
    pos_w = [x0 + 1.5 * sw_, x0 + 3.5 * sw_, x0 + 4.5 * sw_]
    for (g, _), px in zip(right, pos_w):
        b += tag(px, yb + 10, g, w=96)
    for p1, p2 in zip(pos_w, pos_w[1:]):
        b += arrow(p1 + 50, yb + 10, p2 - 50, yb + 10, color=SKILL)
    b += text(x0 + 5 * sw_ + 16, yb + 6, "drei Positionen, drei Wörter,", size=12.5,
              anchor="start", color=SKILL)
    b += text(x0 + 5 * sw_ + 16, yb + 24, "alle Übergänge gültig", size=12.5,
              anchor="start", color=SKILL)
    b += text(W - 30, H - 12, "Subword-Zerlegung schematisch", size=11, anchor="end",
              color=MUTED, style="italic")
    return svg(W, H, b)


if __name__ == "__main__":
    import os
    os.makedirs("diagramme", exist_ok=True)
    for name, fn in [("abb1_pipeline", abb1), ("abb2_architektur", abb2),
                     ("abb3_alignment", abb3)]:
        s = fn()
        open(f"diagramme/{name}.svg", "w", encoding="utf-8").write(s)
        cairosvg.svg2pdf(bytestring=s.encode("utf-8"), write_to=f"diagramme/{name}.pdf")
        cairosvg.svg2png(bytestring=s.encode("utf-8"), write_to=f"diagramme/{name}.png",
                         output_width=2000)
        print("geschrieben:", name)

# Hinweis: echte Subwords fuer das Beispiel holen (z.B. in Kaggle):
#   from transformers import AutoTokenizer
#   print(AutoTokenizer.from_pretrained("xlm-roberta-base").tokenize("Programmierung mit Python"))
# und die Listen `subs`/`toks` sowie die Wortspannen in abb1/abb2/abb3 anpassen.

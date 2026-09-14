"""
Modelle fuer die Skill- und Knowledge-Extraktion.

Aufbau (vgl. SkillSpan, Zhang et al. 2022):

    Tokens -> Transformer-Encoder -> Dropout -> Klassifikationskopf -> Tags

Zwei Varianten des Kopfes (-> Ablation "linear vs. crf"):
  linear: jedes Token wird unabhaengig klassifiziert. Schnell, kann aber
          ungueltige Folgen wie O -> I-SKILL erzeugen.
  crf:    ein Conditional Random Field lernt zusaetzlich, welche Tag-Uebergaenge
          erlaubt bzw. wahrscheinlich sind, und dekodiert die beste Gesamtfolge
          (Viterbi). Das sollte vor allem die Span-Grenzen verbessern.

Zwei Varianten der Aufgabenteilung (-> Ablation "single vs. multi"):
  single: ein Modell pro Ebene (eines fuer Skills, eines fuer Knowledge)
  multi:  ein gemeinsamer Encoder mit zwei Koepfen. Noetig, weil ein Token zu
          einem Skill- UND einem Knowledge-Span gehoeren kann (97 Faelle im
          Train-Set), was mit einem einzigen Tagset nicht darstellbar waere.
"""
import torch
import torch.nn as nn
from transformers import AutoConfig, AutoModel

IGNORE = -100


def compact(emissions, mask, tags=None):
    """Sammelt die gelabelten Positionen (erstes Subword jedes Wortes) zu einer
    LUECKENLOSEN Folge zusammen.

    Noetig, weil der CRF Uebergaenge zwischen aufeinanderfolgenden Positionen modelliert.
    Auf Subword-Ebene stehen zwischen zwei gelabelten Positionen ignorierte Subwords
    ([CLS], Wortfortsetzungen, Padding). Wuerde man die einfach per Maske ueberspringen,
    ergaebe die Gold-Folge "B-SKILL, (ignoriert), I-SKILL" den Uebergang B -> O -> I,
    also eine nach BIO verbotene Kette, und die Loss explodiert.

    Gibt (emissions_kompakt, tags_kompakt, mask_kompakt, index) zurueck;
    index zeigt, an welcher Subword-Position jeder kompakte Eintrag stand.
    """
    batch, _, num_tags = emissions.shape
    counts = mask.sum(1)
    width = max(int(counts.max().item()), 1)
    device = emissions.device
    out_em = emissions.new_zeros(batch, width, num_tags)
    out_mask = torch.zeros(batch, width, dtype=torch.bool, device=device)
    out_idx = torch.zeros(batch, width, dtype=torch.long, device=device)
    out_tags = torch.zeros(batch, width, dtype=torch.long, device=device) if tags is not None else None
    for b in range(batch):
        idx = mask[b].nonzero(as_tuple=True)[0]
        n = idx.numel()
        if n == 0:
            # Satz ohne eine einzige gelabelte Position. Kommt vor, wenn ein "Satz"
            # nur aus Steuerzeichen besteht (z. B. '\u200d') und der Tokenizer alles
            # entfernt. Ohne diesen Fall waere die Folge leer, mask.sum()-1 = -1 und
            # der Zugriff auf Position -1 loest auf der GPU einen device-side assert aus.
            # Ersatz: eine Ein-Token-Folge mit Tag O.
            out_em[b, 0] = emissions[b, 0]
            out_mask[b, 0] = True
            out_idx[b, 0] = 0
            continue
        out_em[b, :n] = emissions[b, idx]
        out_mask[b, :n] = True
        out_idx[b, :n] = idx
        if tags is not None:
            out_tags[b, :n] = tags[b, idx]
    return out_em, out_tags, out_mask, out_idx


class CRF(nn.Module):
    """Lineares Chain-CRF ueber die Tag-Folge eines Satzes.

    Gelernt werden:
      transitions[i, j]  Score fuer den Uebergang von Tag i zu Tag j
      start[j], end[i]   Score fuer Satzanfang und Satzende

    forward() liefert die negative Log-Likelihood der Gold-Folge:
        -log P(gold) = logsumme_ueber_alle_folgen - score(gold)
    decode() sucht mit Viterbi die Folge mit dem hoechsten Score.

    constrain_bio=True verbietet ungueltige BIO-Uebergaenge fest (Score -10000),
    z. B. O -> I-SKILL oder B-SKILL -> I-KNOWLEDGE. Das Original (MaChAmp,
    task_type "seq_bio") macht genau das ueber allowed_transitions('BIO', ...).

    Erwartet LUECKENLOSE Folgen -> vorher compact() aufrufen.
    """

    NEG = -1e4

    def __init__(self, num_tags, id2label=None, constrain_bio=True):
        super().__init__()
        self.num_tags = num_tags
        self.transitions = nn.Parameter(torch.empty(num_tags, num_tags))
        self.start = nn.Parameter(torch.empty(num_tags))
        self.end = nn.Parameter(torch.empty(num_tags))
        for p in (self.transitions, self.start, self.end):
            nn.init.uniform_(p, -0.1, 0.1)
        if constrain_bio and id2label is not None:
            t_mask, s_mask = self._bio_masks(id2label)
        else:
            t_mask = torch.zeros(num_tags, num_tags)
            s_mask = torch.zeros(num_tags)
        self.register_buffer("t_penalty", t_mask)
        self.register_buffer("s_penalty", s_mask)

    @staticmethod
    def _bio_masks(id2label):
        """0 = erlaubt, NEG = verboten."""
        labels = [id2label[i] for i in range(len(id2label))]
        n = len(labels)
        t = torch.zeros(n, n)
        s = torch.zeros(n)
        def parts(tag):
            return (tag, "") if tag == "O" else (tag[0], tag[2:])
        for i, a in enumerate(labels):
            a_pos, a_ent = parts(a)
            for j, b in enumerate(labels):
                b_pos, b_ent = parts(b)
                # I-X ist nur nach B-X oder I-X erlaubt
                if b_pos == "I" and not (a_pos in ("B", "I") and a_ent == b_ent):
                    t[i, j] = CRF.NEG
            if a_pos == "I":       # ein Satz kann nicht mit I- beginnen
                s[i] = CRF.NEG
        return t, s

    def _emit_start(self):
        return self.start + self.s_penalty

    def _emit_trans(self):
        return self.transitions + self.t_penalty

    def _score(self, emissions, tags, mask):
        """Score der tatsaechlichen (Gold-)Folge."""
        trans = self._emit_trans()
        batch, seq_len = tags.shape
        score = self._emit_start()[tags[:, 0]] + emissions[:, 0].gather(1, tags[:, :1]).squeeze(1)
        for i in range(1, seq_len):
            step = trans[tags[:, i - 1], tags[:, i]] + emissions[:, i].gather(1, tags[:, i:i + 1]).squeeze(1)
            score = score + step * mask[:, i]
        last = (mask.sum(1).long() - 1).clamp(min=0)     # Index des letzten echten Tokens
        score = score + self.end[tags.gather(1, last.unsqueeze(1)).squeeze(1)]
        return score

    def _log_partition(self, emissions, mask):
        """log-Summe ueber ALLE moeglichen Folgen (Forward-Algorithmus)."""
        trans = self._emit_trans()
        alpha = self._emit_start() + emissions[:, 0]
        for i in range(1, emissions.size(1)):
            # (batch, from_tag, to_tag)
            nxt = alpha.unsqueeze(2) + trans.unsqueeze(0) + emissions[:, i].unsqueeze(1)
            nxt = torch.logsumexp(nxt, dim=1)
            m = mask[:, i].unsqueeze(1)
            alpha = m * nxt + (1 - m) * alpha              # nach Satzende: alpha einfrieren
        return torch.logsumexp(alpha + self.end, dim=1)

    def forward(self, emissions, tags, mask):
        """Negative Log-Likelihood, gemittelt ueber die Saetze im Batch."""
        mask = mask.float()
        tags = tags.clone()
        tags[tags == IGNORE] = 0                            # Platzhalter; per mask ausgeblendet
        nll = self._log_partition(emissions, mask) - self._score(emissions, tags, mask)
        return nll.mean()

    @torch.no_grad()
    def decode(self, emissions, mask):
        """Viterbi: beste Tag-Folge pro Satz, als Liste unterschiedlicher Laengen."""
        trans = self._emit_trans()
        batch, seq_len, num_tags = emissions.shape
        mask = mask.bool()
        score = self._emit_start() + emissions[:, 0]
        history = []
        for i in range(1, seq_len):
            nxt = score.unsqueeze(2) + trans.unsqueeze(0) + emissions[:, i].unsqueeze(1)
            best, idx = nxt.max(dim=1)
            m = mask[:, i].unsqueeze(1)
            score = torch.where(m, best, score)
            history.append(idx)
        score = score + self.end
        lengths = mask.sum(1)
        best_paths = []
        for b in range(batch):
            n = int(lengths[b])
            tag = int(score[b].argmax())
            path = [tag]
            for i in range(n - 2, -1, -1):                  # rueckwaerts durch die Historie
                tag = int(history[i][b, tag])
                path.append(tag)
            best_paths.append(path[::-1])
        return best_paths


class SpanTagger(nn.Module):
    """Encoder + ein Kopf pro Label-Ebene.

    layers: z. B. ["skill"] (single-task) oder ["skill", "knowledge"] (multi-task)
    """

    def __init__(self, model_name, layers, id2label, decoder="crf", dropout=0.2,
                 freeze_encoder=False, constrain_bio=True):
        super().__init__()
        self.layers, self.decoder = layers, decoder
        config = AutoConfig.from_pretrained(model_name)
        self.encoder = AutoModel.from_pretrained(model_name, config=config)
        self.dropout = nn.Dropout(dropout)
        num_tags = len(id2label[layers[0]])
        self.heads = nn.ModuleDict({l: nn.Linear(config.hidden_size, num_tags) for l in layers})
        self.crfs = (nn.ModuleDict({l: CRF(num_tags, id2label[l], constrain_bio) for l in layers})
                     if decoder == "crf" else None)
        if freeze_encoder:                                  # -> Ablation "frozen encoder"
            for p in self.encoder.parameters():
                p.requires_grad = False

    def forward(self, input_ids, attention_mask, labels=None):
        hidden = self.encoder(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state
        hidden = self.dropout(hidden)
        emissions = {l: self.heads[l](hidden) for l in self.layers}
        if labels is None:
            return emissions, None
        loss = 0.0
        for l in self.layers:
            if self.decoder == "crf":
                # Nur die gelabelten Positionen (erstes Subword je Wort), luecklos zusammengeschoben
                mask = (labels[l] != IGNORE) & attention_mask.bool()
                em_c, tags_c, mask_c, _ = compact(emissions[l], mask, labels[l])
                loss = loss + self.crfs[l](em_c, tags_c, mask_c)
            else:
                loss = loss + nn.functional.cross_entropy(
                    emissions[l].reshape(-1, emissions[l].size(-1)),
                    labels[l].reshape(-1), ignore_index=IGNORE)
        return emissions, loss / len(self.layers)

    @torch.no_grad()
    def predict(self, input_ids, attention_mask, label_mask):
        """Vorhersagen pro Subword. label_mask markiert die Positionen, die ein Label tragen."""
        emissions, _ = self.forward(input_ids, attention_mask)
        out = {}
        mask = label_mask & attention_mask.bool()
        for l in self.layers:
            if self.decoder == "crf":
                em_c, _, mask_c, idx_c = compact(emissions[l], mask)
                paths = self.crfs[l].decode(em_c, mask_c)
                pred = torch.zeros_like(input_ids)          # 0 == "O"
                for b, path in enumerate(paths):
                    if path:
                        pred[b, idx_c[b, :len(path)]] = torch.tensor(path, device=pred.device)
                out[l] = pred
            else:
                out[l] = emissions[l].argmax(-1)
        return out

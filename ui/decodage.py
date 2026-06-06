# ui/decodage.py — Panneau de décodage normatif AISM
#
# Affiche, pour un ensemble de secteurs parsés :
#   - la famille du feu et sa description normée
#   - les durées normées utilisées (éclat, inter-éclat, etc.)
#   - la séquence pas à pas avec annotations
#   - en cas de multi-secteurs hétérogènes : un bloc par secteur fusionné

import tkinter as tk
from tkinter import ttk
from aism import (
    DUREE_ECLAT, DUREE_INTER_ECLAT, DUREE_INTER_GROUPE,
    DUREE_OCCULTATION, COULEURS, N_CYCLES,
    periode_scintillement
)


# ---------------------------------------------------------------------------
# Descriptions normatives des familles
# ---------------------------------------------------------------------------

FAMILLES_DESC = {
    "F":   ("Feu fixe",
            "Le feu est allumé en permanence et de façon constante."),
    "FL":  ("Feu à éclats",
            "La durée de lumière est strictement inférieure à la durée d'obscurité.\n"
            "Chaque éclat dure {eclat}s. L'inter-éclat (dans un groupe) dure {inter}s.\n"
            "L'inter-groupe dure {inter_groupe}s. Le silence final cale la période déclarée."),
    "OC":  ("Feu à occultations",
            "La durée de lumière est strictement supérieure à la durée d'obscurité.\n"
            "Chaque occultation (extinction) dure {oc}s. Le feu reste allumé le reste du temps."),
    "ISO": ("Feu isophase",
            "Durée de lumière égale à la durée d'obscurité : 50% / 50% de la période."),
    "Q":   ("Feu à scintillement",
            "Succession rapide d'éclats à fréquence normée :\n"
            "  Q  (Quick)       : 50 éclats/min  → période éclat = 1.20s\n"
            "  VQ (Very Quick)  : 120 éclats/min → période éclat = 0.50s\n"
            "  UQ (Ultra Quick) : 240 éclats/min → période éclat = 0.25s\n"
            "Interrompu (IQ, IVQ) : groupe de scintillements suivi d'une longue pause."),
}

NORME_DUREES = {
    "eclat":       DUREE_ECLAT,
    "inter":       DUREE_INTER_ECLAT,
    "inter_groupe": DUREE_INTER_GROUPE,
    "oc":          DUREE_OCCULTATION,
}

# Annotations des types de pas
ANNOTATIONS = {
    # (etat, nature) → texte
    ("on",  "eclat"):        "éclat                  (norme AISM : {eclat}s)",
    ("off", "inter_eclat"):  "inter-éclat            (norme AISM : {inter}s)",
    ("off", "inter_groupe"): "inter-groupe           (norme AISM : {inter_groupe}s)",
    ("off", "occultation"):  "occultation            (norme AISM : {oc}s)",
    ("on",  "lumiere_oc"):   "lumière (hors occultation)",
    ("off", "silence"):      "silence final          (calage sur la période déclarée)",
    ("on",  "fixe"):         "feu fixe               (allumé en permanence)",
    ("on",  "scintillement"):"demi-période ON        (scintillement)",
    ("off", "scintillement"):"demi-période OFF       (scintillement)",
}


def _annoter_sequence(sequence: list, famille: str) -> list:
    """
    Associe une annotation normative à chaque pas de la séquence.
    Retourne une liste de (step, annotation_str).
    """
    annotated = []
    n = len(sequence)

    if famille == "F":
        for step in sequence:
            annotated.append((step, ANNOTATIONS[("on", "fixe")]))
        return annotated

    if famille == "ISO":
        for i, step in enumerate(sequence):
            key = "on" if step["etat"] == "on" else "off"
            txt = "lumière (50% de la période)" if key == "on" else "obscurité (50% de la période)"
            annotated.append((step, txt))
        return annotated

    if famille == "Q":
        for i, step in enumerate(sequence):
            if step["etat"] == "on":
                annotated.append((step, ANNOTATIONS[("on",  "scintillement")]))
            else:
                # Dernier off long = silence final si interrompu
                if i == n - 1 and step["duree"] > DUREE_INTER_ECLAT * 2:
                    annotated.append((step, ANNOTATIONS[("off", "silence")].format(**NORME_DUREES)))
                else:
                    annotated.append((step, ANNOTATIONS[("off", "scintillement")]))
        return annotated

    if famille == "OC":
        for i, step in enumerate(sequence):
            if step["etat"] == "off":
                if abs(step["duree"] - DUREE_OCCULTATION) < 0.05:
                    annotated.append((step, ANNOTATIONS[("off", "occultation")].format(**NORME_DUREES)))
                elif abs(step["duree"] - DUREE_INTER_ECLAT) < 0.05:
                    annotated.append((step, ANNOTATIONS[("off", "inter_eclat")].format(**NORME_DUREES)))
                else:
                    annotated.append((step, "obscurité résiduelle"))
            else:
                annotated.append((step, ANNOTATIONS[("on", "lumiere_oc")]))
        return annotated

    # FL — éclats
    for i, step in enumerate(sequence):
        if step["etat"] == "on":
            annotated.append((step, ANNOTATIONS[("on", "eclat")].format(**NORME_DUREES)))
        else:
            # Identifier la nature du silence
            if abs(step["duree"] - DUREE_INTER_ECLAT) < 0.05:
                annotated.append((step, ANNOTATIONS[("off", "inter_eclat")].format(**NORME_DUREES)))
            elif abs(step["duree"] - DUREE_INTER_GROUPE) < 0.05:
                annotated.append((step, ANNOTATIONS[("off", "inter_groupe")].format(**NORME_DUREES)))
            else:
                # Silence final
                annotated.append((step, ANNOTATIONS[("off", "silence")].format(**NORME_DUREES)))

    return annotated


def _detecter_famille(secteurs: list) -> str:
    """Retourne la famille du premier secteur (portée par le parser)."""
    if not secteurs:
        return "F"
    return secteurs[0].get("famille", "FL")


def _sequences_identiques(secteurs: list) -> bool:
    """Vérifie si tous les secteurs ont la même séquence (même cadence)."""
    if len(secteurs) <= 1:
        return True
    ref = [(s["etat"], s["duree"]) for s in secteurs[0]["sequence"]]
    for sec in secteurs[1:]:
        autre = [(s["etat"], s["duree"]) for s in sec["sequence"]]
        if autre != ref:
            return False
    return True


# ---------------------------------------------------------------------------
# Widget principal
# ---------------------------------------------------------------------------

class PanneauDecodage:
    """
    Panneau rétractable affichant le décodage normatif du code AISM courant.
    """

    def __init__(self, parent: tk.Widget):
        self.parent = parent
        self._ouvert = True

        # Conteneur principal
        self.frame = tk.Frame(parent, bg="#1E1E1E")
        self.frame.pack(fill=tk.X, padx=0, pady=0)

        # En-tête cliquable (toggle)
        self.header = tk.Frame(self.frame, bg="#252525", cursor="hand2")
        self.header.pack(fill=tk.X)
        self.header.bind("<Button-1>", self._toggle)

        self.var_toggle = tk.StringVar(value="▼  Décodage normatif AISM")
        tk.Label(
            self.header,
            textvariable=self.var_toggle,
            bg="#252525", fg="#AAAAAA",
            font=("Helvetica", 9, "bold"),
            anchor=tk.W, padx=10, pady=4
        ).pack(side=tk.LEFT)
        self.header.bind("<Button-1>", self._toggle)

        # Corps du panneau (scrollable)
        self.corps_outer = tk.Frame(self.frame, bg="#161616")
        self.corps_outer.pack(fill=tk.X)

        self.canvas_scroll = tk.Canvas(
            self.corps_outer,
            bg="#161616",
            highlightthickness=0,
            height=0  # sera ajusté
        )
        self.scrollbar = ttk.Scrollbar(
            self.corps_outer,
            orient="vertical",
            command=self.canvas_scroll.yview
        )
        self.canvas_scroll.configure(yscrollcommand=self.scrollbar.set)

        self.corps = tk.Frame(self.canvas_scroll, bg="#161616")
        self.canvas_window = self.canvas_scroll.create_window(
            (0, 0), window=self.corps, anchor="nw"
        )

        self.corps.bind("<Configure>", self._on_corps_configure)
        self.canvas_scroll.bind("<Configure>", self._on_canvas_configure)

    def _on_corps_configure(self, event):
        self.canvas_scroll.configure(scrollregion=self.canvas_scroll.bbox("all"))
        h = min(self.corps.winfo_reqheight(), 220)
        self.canvas_scroll.configure(height=h)
        if self.corps.winfo_reqheight() > 220:
            self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        else:
            self.scrollbar.pack_forget()

    def _on_canvas_configure(self, event):
        self.canvas_scroll.itemconfig(self.canvas_window, width=event.width)

    def _toggle(self, event=None):
        self._ouvert = not self._ouvert
        if self._ouvert:
            self.canvas_scroll.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.var_toggle.set("▼  Décodage normatif AISM")
        else:
            self.canvas_scroll.pack_forget()
            self.scrollbar.pack_forget()
            self.var_toggle.set("▶  Décodage normatif AISM")

    # -----------------------------------------------------------------------
    # Rendu du contenu
    # -----------------------------------------------------------------------

    def charger(self, secteurs: list, code_original: str):
        """Remplit le panneau avec le décodage des secteurs."""
        # Nettoyage
        for w in self.corps.winfo_children():
            w.destroy()

        if not secteurs:
            return

        famille = _detecter_famille(secteurs)
        meme_cadence = _sequences_identiques(secteurs)
        heterogenes = not meme_cadence

        # --- En-tête : code + famille ---
        self._ligne_titre(f"Code :  {code_original}", "#DDDDDD")
        nom_famille, desc_famille = FAMILLES_DESC.get(famille, ("Inconnu", ""))
        self._ligne_titre(f"Famille : {nom_famille}", "#AAAAFF")

        desc_formatee = desc_famille.format(**NORME_DUREES)
        self._texte(desc_formatee, "#888888")

        self._separateur()

        # --- Secteurs ---
        if heterogenes:
            # Un sous-bloc par secteur
            for i, sec in enumerate(secteurs):
                fam_sec = _detecter_famille([sec])
                self._ligne_titre(
                    f"Secteur {i+1} — {sec['label']}  |  T = {sec['periode']:.2f}s",
                    sec["hex"]
                )
                self._afficher_sequence(sec["sequence"], fam_sec)
                if i < len(secteurs) - 1:
                    self._separateur(leger=True)
        else:
            # Cadence commune — un seul bloc, couleurs listées
            couleurs_str = "  /  ".join(
                f"{s['label']}" for s in secteurs
            )
            self._ligne_titre(
                f"Secteurs : {couleurs_str}  |  T = {secteurs[0]['periode']:.2f}s  "
                f"(cadence identique sur tous les secteurs)",
                "#AAAAAA"
            )
            self._afficher_sequence(secteurs[0]["sequence"], famille)

        self._separateur()

        # --- Rappel norme ---
        self._ligne_titre("Rappel des durées normées AISM", "#888888")
        normes = [
            ("Éclat",                f"{DUREE_ECLAT}s"),
            ("Inter-éclat",          f"{DUREE_INTER_ECLAT}s"),
            ("Inter-groupe",         f"{DUREE_INTER_GROUPE}s"),
            ("Occultation brève",    f"{DUREE_OCCULTATION}s"),
            ("Scintillement Q",      f"{60/50:.2f}s / éclat  (50 éclats/min)"),
            ("Scintillement VQ",     f"{60/120:.2f}s / éclat  (120 éclats/min)"),
            ("Scintillement UQ",     f"{60/240:.3f}s / éclat  (240 éclats/min)"),
            ("Diagramme : cycles",   f"{N_CYCLES} cycles du secteur de période max"),
        ]
        for label, valeur in normes:
            self._ligne_norme(label, valeur)

        # Ouvrir si fermé
        if not self._ouvert:
            self._toggle()

        self.canvas_scroll.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _afficher_sequence(self, sequence: list, famille: str):
        """Affiche la séquence pas à pas avec annotations."""
        annotated = _annoter_sequence(sequence, famille)
        n = len(annotated)

        frame_seq = tk.Frame(self.corps, bg="#161616")
        frame_seq.pack(fill=tk.X, padx=16, pady=(2, 4))

        for i, (step, annotation) in enumerate(annotated):
            est_dernier = (i == n - 1)
            branche = "└─" if est_dernier else "├─"
            etat_str = "ON " if step["etat"] == "on" else "OFF"
            couleur_etat = "#88FF88" if step["etat"] == "on" else "#FF8888"
            duree_str = f"{step['duree']:.3f}s"

            ligne = tk.Frame(frame_seq, bg="#161616")
            ligne.pack(fill=tk.X, pady=0)

            tk.Label(
                ligne, text=f"  {branche} ",
                bg="#161616", fg="#555555",
                font=("Courier", 9)
            ).pack(side=tk.LEFT)

            tk.Label(
                ligne, text=etat_str,
                bg="#161616", fg=couleur_etat,
                font=("Courier", 9, "bold"),
                width=4
            ).pack(side=tk.LEFT)

            tk.Label(
                ligne, text=f"{duree_str:>8}",
                bg="#161616", fg="#DDDDDD",
                font=("Courier", 9),
                width=9
            ).pack(side=tk.LEFT)

            tk.Label(
                ligne, text=f"  ←  {annotation}",
                bg="#161616", fg="#777777",
                font=("Helvetica", 8)
            ).pack(side=tk.LEFT)

    # -----------------------------------------------------------------------
    # Helpers d'affichage
    # -----------------------------------------------------------------------

    def _ligne_titre(self, texte: str, couleur: str):
        tk.Label(
            self.corps, text=texte,
            bg="#161616", fg=couleur,
            font=("Helvetica", 9, "bold"),
            anchor=tk.W, padx=12, pady=2
        ).pack(fill=tk.X)

    def _texte(self, texte: str, couleur: str):
        tk.Label(
            self.corps, text=texte,
            bg="#161616", fg=couleur,
            font=("Helvetica", 8),
            anchor=tk.W, padx=20, pady=1,
            justify=tk.LEFT
        ).pack(fill=tk.X)

    def _separateur(self, leger: bool = False):
        couleur = "#2A2A2A" if leger else "#333333"
        tk.Frame(self.corps, bg=couleur, height=1).pack(fill=tk.X, pady=3)

    def _ligne_norme(self, label: str, valeur: str):
        ligne = tk.Frame(self.corps, bg="#161616")
        ligne.pack(fill=tk.X, padx=20, pady=0)
        tk.Label(
            ligne, text=f"{label:<25}",
            bg="#161616", fg="#666666",
            font=("Courier", 8),
            width=26, anchor=tk.W
        ).pack(side=tk.LEFT)
        tk.Label(
            ligne, text=valeur,
            bg="#161616", fg="#999999",
            font=("Courier", 8),
            anchor=tk.W
        ).pack(side=tk.LEFT)

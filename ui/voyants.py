# ui/voyants.py — Voyants animés en temps réel, un par secteur

import tkinter as tk
from aism import ETEINT_HEX, COULEURS


class Voyant:
    """
    Voyant animé pour un secteur.
    Gère son propre état interne et son avancement dans la séquence.
    """

    RAYON = 40  # px
    LARGEUR = 120
    HAUTEUR = 120

    def __init__(self, parent: tk.Frame, secteur: dict):
        self.secteur  = secteur
        self.sequence = secteur["sequence"]
        self.hex_on   = secteur["hex"]
        self.label    = secteur["label"]

        # État interne
        self._step_idx    = 0
        self._temps_restant = self.sequence[0]["duree"] if self.sequence else 1.0
        self._allume      = False
        self._after_id    = None

        # Construction du widget
        self.frame = tk.Frame(parent, bg="#1E1E1E")
        self.frame.pack(side=tk.LEFT, padx=12, pady=8)

        self.canvas = tk.Canvas(
            self.frame,
            width=self.LARGEUR,
            height=self.HAUTEUR,
            bg="#1E1E1E",
            highlightthickness=0
        )
        self.canvas.pack()

        cx = self.LARGEUR // 2
        cy = self.HAUTEUR // 2 - 10

        # Cercle du voyant
        self.oval = self.canvas.create_oval(
            cx - self.RAYON, cy - self.RAYON,
            cx + self.RAYON, cy + self.RAYON,
            fill=ETEINT_HEX,
            outline="#444444",
            width=2
        )

        # Halo (cercle extérieur, visible quand allumé)
        self.halo = self.canvas.create_oval(
            cx - self.RAYON - 6, cy - self.RAYON - 6,
            cx + self.RAYON + 6, cy + self.RAYON + 6,
            fill="",
            outline="",
            width=0
        )

        # Label couleur/secteur
        self.canvas.create_text(
            cx, self.HAUTEUR - 12,
            text=self.label,
            fill=self.hex_on,
            font=("Helvetica", 9, "bold")
        )

    def demarrer(self):
        """Lance l'animation."""
        if self.sequence:
            self._step_idx = 0
            self._appliquer_step()

    def arreter(self):
        """Stoppe l'animation."""
        if self._after_id:
            self.frame.after_cancel(self._after_id)
            self._after_id = None
        self._set_etat(False)

    def _appliquer_step(self):
        """Applique le pas courant et programme le suivant."""
        if not self.sequence:
            return

        step = self.sequence[self._step_idx]
        self._set_etat(step["etat"] == "on")

        delai_ms = max(1, int(step["duree"] * 1000))
        self._after_id = self.frame.after(delai_ms, self._pas_suivant)

    def _pas_suivant(self):
        """Avance au pas suivant, boucle en fin de séquence."""
        self._step_idx = (self._step_idx + 1) % len(self.sequence)
        self._appliquer_step()

    def _set_etat(self, allume: bool):
        """Met à jour l'affichage du voyant."""
        self._allume = allume
        if allume:
            self.canvas.itemconfig(self.oval, fill=self.hex_on)
            self.canvas.itemconfig(
                self.halo,
                outline=self.hex_on,
                width=3
            )
        else:
            self.canvas.itemconfig(self.oval, fill=ETEINT_HEX)
            self.canvas.itemconfig(self.halo, outline="", width=0)


class PanneauVoyants:
    """
    Panneau contenant tous les voyants des secteurs.
    """

    def __init__(self, parent: tk.Frame):
        self.parent  = parent
        self.voyants = []

        self.frame = tk.Frame(parent, bg="#1E1E1E")
        self.frame.pack(fill=tk.X, padx=10, pady=5)

        self.titre = tk.Label(
            self.frame,
            text="Secteurs",
            bg="#1E1E1E",
            fg="#888888",
            font=("Helvetica", 9)
        )
        self.titre.pack(anchor=tk.W, padx=8)

        self.conteneur = tk.Frame(self.frame, bg="#1E1E1E")
        self.conteneur.pack(fill=tk.X)

    def charger(self, secteurs: list):
        """Charge et anime les voyants pour une liste de secteurs."""
        self.arreter()

        # Nettoyage
        for widget in self.conteneur.winfo_children():
            widget.destroy()
        self.voyants = []

        # Création des voyants
        for secteur in secteurs:
            v = Voyant(self.conteneur, secteur)
            self.voyants.append(v)

        # Démarrage synchronisé
        for v in self.voyants:
            v.demarrer()

    def arreter(self):
        """Stoppe tous les voyants."""
        for v in self.voyants:
            v.arreter()

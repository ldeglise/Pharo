# main.py — Fenêtre principale du visualiseur de phares AISM

import tkinter as tk
from tkinter import ttk, messagebox

from parser import parse
from ui.voyants import PanneauVoyants
from ui.diagramme import afficher_diagramme
from ui.decodage import PanneauDecodage


# ---------------------------------------------------------------------------
# Exemples de codes pour la liste déroulante
# ---------------------------------------------------------------------------

EXEMPLES = [
    ("Feu fixe blanc",                   "F W"),
    ("Éclat simple 10s",                 "Fl W 10s"),
    ("Éclat rouge 5s",                   "Fl R 5s"),
    ("Éclats groupés (2) blanc 10s",     "Fl(2) W 10s"),
    ("Éclats groupés (3) WRG 15s",       "Fl(3) WRG 15s"),
    ("Éclats composés (2+1) 15s",        "Fl(2+1) W 15s"),
    ("Occultation simple blanc 4s",      "Oc W 4s"),
    ("Occultations groupées (2) R 10s",  "Oc(2) R 10s"),
    ("Isophase blanc 4s",                "Iso W 4s"),
    ("Scintillement Q vert",             "Q G"),
    ("Scintillement rapide VQ blanc",    "VQ W"),
    ("Scintillement groupé Q(3) 10s",   "Q(3) W 10s"),
    ("Scintillement interrompu IQ R",    "IQ R 15s"),
    ("Multi-secteurs hétérogènes",       "F W / Fl R 5s / Q G"),
    ("Multi-secteurs (2) WRG 10s",       "Fl(2) WRG 10s"),
]


# ---------------------------------------------------------------------------
# Fenêtre principale
# ---------------------------------------------------------------------------

class AppPhare(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Visualiseur de phares AISM")
        self.configure(bg="#1E1E1E")
        self.resizable(True, True)
        self.minsize(700, 550)

        self._secteurs_courants = []
        self._panneau_voyants   = None
        self._panneau_decodage  = None

        self._build_ui()
        self.after(100, lambda: self._valider(EXEMPLES[0][1]))

    # -----------------------------------------------------------------------
    # Construction de l'interface
    # -----------------------------------------------------------------------

    def _build_ui(self):
        """Construit tous les widgets de la fenêtre."""

        # --- Barre de saisie ---
        frame_saisie = tk.Frame(self, bg="#2A2A2A", pady=8)
        frame_saisie.pack(fill=tk.X, padx=0, pady=0)

        tk.Label(
            frame_saisie, text="Code AISM :",
            bg="#2A2A2A", fg="#AAAAAA",
            font=("Helvetica", 10)
        ).pack(side=tk.LEFT, padx=(12, 4))

        self.var_code = tk.StringVar()
        self.entry = tk.Entry(
            frame_saisie,
            textvariable=self.var_code,
            font=("Courier", 12),
            bg="#121212", fg="#FFFFFF",
            insertbackground="#FFFFFF",
            relief=tk.FLAT,
            width=30
        )
        self.entry.pack(side=tk.LEFT, padx=4, ipady=4)
        self.entry.bind("<Return>", lambda e: self._valider())

        tk.Button(
            frame_saisie, text="Afficher",
            command=self._valider,
            bg="#3A6EA5", fg="white",
            relief=tk.FLAT,
            font=("Helvetica", 10, "bold"),
            padx=12, pady=2,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=8)

        # Exemples
        tk.Label(
            frame_saisie, text="Exemples :",
            bg="#2A2A2A", fg="#888888",
            font=("Helvetica", 9)
        ).pack(side=tk.LEFT, padx=(20, 4))

        self.var_exemple = tk.StringVar()
        combo = ttk.Combobox(
            frame_saisie,
            textvariable=self.var_exemple,
            values=[f"{label}  →  {code}" for label, code in EXEMPLES],
            state="readonly",
            width=40,
            font=("Helvetica", 9)
        )
        combo.pack(side=tk.LEFT, padx=4)
        combo.bind("<<ComboboxSelected>>", self._charger_exemple)

        # Style combobox sombre
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "TCombobox",
            fieldbackground="#121212",
            background="#2A2A2A",
            foreground="#CCCCCC",
            selectbackground="#3A6EA5",
            selectforeground="white"
        )

        # --- Label d'info (code décodé) ---
        self.var_info = tk.StringVar(value="")
        tk.Label(
            self,
            textvariable=self.var_info,
            bg="#1E1E1E", fg="#888888",
            font=("Helvetica", 9),
            anchor=tk.W
        ).pack(fill=tk.X, padx=14, pady=(4, 0))

        # --- Séparateur ---
        tk.Frame(self, bg="#333333", height=1).pack(fill=tk.X, pady=4)

        # --- Panneau décodage normatif ---
        self._panneau_decodage = PanneauDecodage(self)

        # --- Séparateur ---
        tk.Frame(self, bg="#333333", height=1).pack(fill=tk.X, pady=4)

        # --- Panneau voyants ---
        self._panneau_voyants = PanneauVoyants(self)

        # --- Séparateur ---
        tk.Frame(self, bg="#333333", height=1).pack(fill=tk.X, pady=4)

        # --- Frame diagramme ---
        self.frame_diagramme = tk.Frame(self, bg="#1E1E1E")
        self.frame_diagramme.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    # -----------------------------------------------------------------------
    # Actions
    # -----------------------------------------------------------------------

    def _charger_exemple(self, event=None):
        """Charge un exemple depuis la combobox."""
        selection = self.var_exemple.get()
        # Extraction du code après la flèche
        if "→" in selection:
            code = selection.split("→")[-1].strip()
            self.var_code.set(code)
            self._valider(code)

    def _valider(self, code: str = None):
        """Parse et affiche le code courant."""
        if code is None:
            code = self.var_code.get().strip()
        else:
            self.var_code.set(code)

        if not code:
            return

        try:
            secteurs = parse(code)
            self._secteurs_courants = secteurs

            # Info de décodage
            resume = "  |  ".join(
                f"{s['label']} T={s['periode']:.1f}s"
                for s in secteurs
            )
            self._afficher_info(f"✓  {code}   →   {resume}")

            # Décodage normatif
            self._panneau_decodage.charger(secteurs, code)

            # Voyants
            self._panneau_voyants.charger(secteurs)

            # Diagramme
            afficher_diagramme(self.frame_diagramme, secteurs)

        except Exception as e:
            self._afficher_info(f"✗  Erreur : {e}", erreur=True)

    def _afficher_info(self, msg: str, erreur: bool = False):
        self.var_info.set(msg)
        # Couleur selon état
        couleur = "#FF6644" if erreur else "#66AA66"
        for widget in self.winfo_children():
            if isinstance(widget, tk.Label) and widget.cget("textvariable") == str(self.var_info):
                widget.config(fg=couleur)
                break

    def on_closing(self):
        """Nettoyage propre à la fermeture."""
        if self._panneau_voyants:
            self._panneau_voyants.arreter()
        self.destroy()


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = AppPhare()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()

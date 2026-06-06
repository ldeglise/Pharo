# ui/diagramme.py — Diagramme temporel matplotlib embarqué dans tkinter

import tkinter as tk
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from aism import N_CYCLES, COULEURS


def construire_signal(sequence: list, n_cycles: int) -> tuple:
    """
    Construit les vecteurs temps/valeur pour un signal numérique en escalier.
    Retourne (t, y) prêts pour plt.step().
    """
    t = [0.0]
    y = [0.0]
    periode = sum(s["duree"] for s in sequence)
    duree_totale = periode * n_cycles

    temps = 0.0
    for _ in range(n_cycles):
        for step in sequence:
            val = 1.0 if step["etat"] == "on" else 0.0
            t.append(temps)
            y.append(val)
            temps += step["duree"]
            t.append(temps)
            y.append(val)

    return t, y, duree_totale


def couleur_matplotlib(hex_color: str, etat: str) -> str:
    """Retourne la couleur matplotlib selon l'état."""
    return hex_color if etat == "on" else "#1A1A1A"


def afficher_diagramme(frame_parent: tk.Frame, secteurs: list):
    """
    Génère et affiche le diagramme temporel dans le frame tkinter fourni.
    Un subplot par secteur, signaux superposés sur le même axe X.
    """
    # Nettoyage du frame
    for widget in frame_parent.winfo_children():
        widget.destroy()

    if not secteurs:
        return

    # Calcul du nombre de cycles : N_CYCLES du secteur de période max
    periodes = [s["periode"] for s in secteurs]
    periode_max = max(periodes)
    duree_totale = periode_max * N_CYCLES

    n_secteurs = len(secteurs)

    fig, axes = plt.subplots(
        n_secteurs, 1,
        figsize=(10, max(2, 1.5 * n_secteurs)),
        sharex=True,
        facecolor="#1E1E1E"
    )

    if n_secteurs == 1:
        axes = [axes]

    fig.subplots_adjust(hspace=0.1, left=0.08, right=0.98, top=0.92, bottom=0.12)
    fig.suptitle("Diagramme temporel", color="#CCCCCC", fontsize=11, fontweight="bold")

    for ax, secteur in zip(axes, secteurs):
        hex_col = secteur["hex"]
        label   = secteur["label"]
        seq     = secteur["sequence"]
        periode = secteur["periode"]

        # Nombre de cycles pour ce secteur pour couvrir duree_totale
        n_cy = max(1, round(duree_totale / periode))

        t, y, _ = construire_signal(seq, n_cy)

        # Fond sombre
        ax.set_facecolor("#121212")

        # Tracé du signal
        ax.step(t, y, where="post", color=hex_col, linewidth=1.5)

        # Remplissage sous la courbe
        ax.fill_between(t, y, step="post", alpha=0.3, color=hex_col)

        # Marqueurs de période
        for k in range(1, n_cy + 1):
            ax.axvline(x=periode * k, color="#444444", linewidth=0.5, linestyle="--")

        # Mise en forme
        ax.set_ylim(-0.1, 1.3)
        ax.set_xlim(0, duree_totale)
        ax.set_yticks([])
        ax.tick_params(colors="#888888", labelsize=8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_visible(False)
        ax.spines["bottom"].set_color("#444444")

        # Label secteur
        ax.text(
            0.005, 0.75, label,
            transform=ax.transAxes,
            color=hex_col,
            fontsize=9,
            fontweight="bold",
            va="top"
        )

        # Annotation période
        ax.text(
            0.995, 0.75,
            f"T = {periode:.1f}s",
            transform=ax.transAxes,
            color="#888888",
            fontsize=8,
            va="top",
            ha="right"
        )

    axes[-1].set_xlabel("Temps (s)", color="#AAAAAA", fontsize=9)

    # Intégration dans tkinter
    canvas = FigureCanvasTkAgg(fig, master=frame_parent)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    plt.close(fig)

# aism.py — Constantes normées AISM / IALA pour la signalisation maritime

# Durées standard en secondes
DUREE_ECLAT        = 0.5   # Durée d'un éclat simple
DUREE_INTER_ECLAT  = 0.5   # Silence entre deux éclats d'un même groupe
DUREE_INTER_GROUPE = 1.0   # Silence entre deux groupes d'éclats
DUREE_OCCULTATION  = 0.5   # Durée d'une occultation brève

# Scintillement : nombre d'éclats par minute → période en secondes
SCINTILLEMENT_Q  = 50   # Quick         : 50/min  → 1.2s  par éclat
SCINTILLEMENT_VQ = 120  # Very Quick    : 120/min → 0.5s  par éclat
SCINTILLEMENT_UQ = 240  # Ultra Quick   : 240/min → 0.25s par éclat

def periode_scintillement(type_q: str) -> float:
    """Retourne la période d'un éclat de scintillement en secondes."""
    mapping = {
        "Q":  60.0 / SCINTILLEMENT_Q,
        "VQ": 60.0 / SCINTILLEMENT_VQ,
        "UQ": 60.0 / SCINTILLEMENT_UQ,
    }
    return mapping.get(type_q, 60.0 / SCINTILLEMENT_Q)

# Correspondance couleurs AISM → RGB tkinter et labels
COULEURS = {
    "W": {"hex": "#FFFFFF", "label": "Blanc",  "fond": "#AAAAAA"},
    "R": {"hex": "#FF2200", "label": "Rouge",  "fond": "#330000"},
    "G": {"hex": "#00CC44", "label": "Vert",   "fond": "#003311"},
    "Y": {"hex": "#FFD700", "label": "Jaune",  "fond": "#332200"},
    "B": {"hex": "#4488FF", "label": "Bleu",   "fond": "#001133"},
}

COULEUR_DEFAUT = "W"

# Couleur éteinte (voyant off)
ETEINT_HEX = "#1A1A1A"

# Nombre de cycles à afficher pour le secteur le plus long
N_CYCLES = 3

# parser.py — Décodage des codes AISM vers séquences temporelles

import re
from aism import (
    DUREE_ECLAT, DUREE_INTER_ECLAT, DUREE_INTER_GROUPE,
    DUREE_OCCULTATION, COULEURS, COULEUR_DEFAUT,
    periode_scintillement
)


# ---------------------------------------------------------------------------
# Structures de données
# ---------------------------------------------------------------------------

def make_step(etat: str, duree: float) -> dict:
    """Crée un pas de séquence : etat='on'|'off', duree en secondes."""
    return {"etat": etat, "duree": round(duree, 4)}


def make_secteur(couleur: str, sequence: list, label_override: str = None, famille: str = None) -> dict:
    """Crée un secteur avec sa couleur et sa séquence temporelle."""
    info = COULEURS.get(couleur, COULEURS[COULEUR_DEFAUT])
    return {
        "couleur":  couleur,
        "hex":      info["hex"],
        "fond":     info["fond"],
        "label":    label_override or info["label"],
        "sequence": sequence,
        "periode":  sum(s["duree"] for s in sequence),
        "famille":  famille or "FL",
    }


# ---------------------------------------------------------------------------
# Extraction des composantes d'un code simple
# ---------------------------------------------------------------------------

def extraire_couleurs(token: str) -> list:
    """
    Extrait la liste des couleurs depuis un token comme 'WRG', 'W', 'RG', etc.
    Retourne une liste de codes couleur ex: ['W', 'R', 'G']
    """
    couleurs = []
    i = 0
    while i < len(token):
        # Couleur sur 1 lettre
        if token[i] in COULEURS:
            couleurs.append(token[i])
            i += 1
        else:
            i += 1
    return couleurs if couleurs else [COULEUR_DEFAUT]


def extraire_periode(tokens: list) -> float:
    """Extrait la période totale en secondes depuis les tokens (ex: '10s' → 10.0)."""
    for t in tokens:
        m = re.match(r'^(\d+(?:\.\d+)?)s$', t, re.IGNORECASE)
        if m:
            return float(m.group(1))
    return None


def extraire_groupes(type_feu: str):
    """
    Extrait les groupes depuis le type de feu.
    'Fl(2+1)' → [2, 1]
    'Fl(3)'   → [3]
    'Fl'      → [1]
    'Oc(2)'   → [2]
    """
    m = re.search(r'\(([^)]+)\)', type_feu)
    if not m:
        return [1]
    contenu = m.group(1)
    parts = contenu.split('+')
    try:
        return [int(p.strip()) for p in parts]
    except ValueError:
        return [1]


# ---------------------------------------------------------------------------
# Générateurs de séquences par famille
# ---------------------------------------------------------------------------

def sequence_fixe(periode: float) -> list:
    """F — feu fixe : toujours allumé."""
    p = periode if periode else 4.0
    return [make_step("on", p)]


def sequence_eclat(groupes: list, periode: float) -> list:
    """
    Fl — éclats groupés.
    groupes = [2, 1] pour Fl(2+1), [3] pour Fl(3), [1] pour Fl simple.
    La période totale est respectée via un silence final.
    """
    seq = []
    duree_active = 0.0

    for idx_groupe, nb_eclats in enumerate(groupes):
        for i in range(nb_eclats):
            seq.append(make_step("on",  DUREE_ECLAT))
            duree_active += DUREE_ECLAT
            if i < nb_eclats - 1:
                seq.append(make_step("off", DUREE_INTER_ECLAT))
                duree_active += DUREE_INTER_ECLAT
        # Silence inter-groupe (sauf après le dernier groupe)
        if idx_groupe < len(groupes) - 1:
            seq.append(make_step("off", DUREE_INTER_GROUPE))
            duree_active += DUREE_INTER_GROUPE

    # Silence final pour boucler sur la période
    if periode:
        silence_final = periode - duree_active
        if silence_final > 0:
            seq.append(make_step("off", silence_final))
    else:
        seq.append(make_step("off", DUREE_INTER_GROUPE * 2))

    return seq


def sequence_occultation(groupes: list, periode: float) -> list:
    """
    Oc — occultations groupées.
    Le feu est allumé la majorité du temps, s'éteint brièvement.
    """
    seq = []
    duree_active = 0.0
    nb_oc = groupes[0] if groupes else 1

    # Calcul de la durée totale d'obscurité
    duree_obscurite = nb_oc * DUREE_OCCULTATION + (nb_oc - 1) * DUREE_INTER_ECLAT
    duree_lumiere = (periode - duree_obscurite) if periode else (nb_oc * 2.0)

    # Lumière initiale
    if duree_lumiere > 0:
        seq.append(make_step("on", duree_lumiere / 2))
        duree_active += duree_lumiere / 2

    for i in range(nb_oc):
        seq.append(make_step("off", DUREE_OCCULTATION))
        duree_active += DUREE_OCCULTATION
        if i < nb_oc - 1:
            seq.append(make_step("on", DUREE_INTER_ECLAT))
            duree_active += DUREE_INTER_ECLAT

    # Lumière finale
    reste = (periode - duree_active) if periode else duree_lumiere / 2
    if reste > 0:
        seq.append(make_step("on", reste))

    return seq


def sequence_isophase(periode: float) -> list:
    """Iso — isophase : 50% allumé / 50% éteint."""
    p = periode if periode else 4.0
    demi = p / 2.0
    return [
        make_step("on",  demi),
        make_step("off", demi),
    ]


def sequence_scintillement(type_q: str, groupes: list, periode: float, interrompu: bool) -> list:
    """
    Q, VQ, UQ — scintillement, éventuellement groupé ou interrompu.
    Interrompu (IQ, IVQ) : groupe d'éclats rapides + longue pause.
    """
    periode_eclat = periode_scintillement(type_q)
    duree_on  = periode_eclat * 0.5
    duree_off = periode_eclat * 0.5

    if interrompu and periode:
        # Groupe de scintillements + pause longue
        nb = groupes[0] if groupes else 6
        seq = []
        duree_active = 0.0
        for i in range(nb):
            seq.append(make_step("on",  duree_on))
            seq.append(make_step("off", duree_off))
            duree_active += periode_eclat
        silence = periode - duree_active
        if silence > 0:
            seq.append(make_step("off", silence))
        return seq
    elif groupes and groupes[0] > 1 and periode:
        # Scintillement groupé Q(3)
        nb = groupes[0]
        seq = []
        duree_active = 0.0
        for i in range(nb):
            seq.append(make_step("on",  duree_on))
            seq.append(make_step("off", duree_off))
            duree_active += periode_eclat
        silence = periode - duree_active
        if silence > 0:
            seq.append(make_step("off", silence))
        return seq
    else:
        # Scintillement continu : on répète sur la période
        if periode:
            nb = max(1, int(periode / periode_eclat))
        else:
            nb = 10
        seq = []
        for _ in range(nb):
            seq.append(make_step("on",  duree_on))
            seq.append(make_step("off", duree_off))
        return seq


# ---------------------------------------------------------------------------
# Parser d'un code simple (un seul secteur)
# ---------------------------------------------------------------------------

def parse_code_simple(code: str) -> dict:
    """
    Parse un code AISM simple et retourne un dict secteur.
    Exemples : 'Fl(2) WRG 10s', 'Oc R 4s', 'Q G', 'F W', 'Iso 4s'
    Retourne un dict avec 'couleurs' (liste) et 'sequence_base'.
    """
    code = code.strip()
    tokens = code.split()

    if not tokens:
        raise ValueError(f"Code vide : '{code}'")

    # --- Détection du type de feu ---
    type_raw = tokens[0].upper()

    # Scintillement interrompu
    interrompu = type_raw.startswith("I") and type_raw[1:] in ("Q", "VQ", "UQ")
    if interrompu:
        type_q = type_raw[1:]
    else:
        type_q = None

    # Famille
    if type_raw == "F":
        famille = "F"
    elif type_raw.startswith("FL") or type_raw.startswith("FL"):
        famille = "FL"
    elif type_raw.startswith("OC"):
        famille = "OC"
    elif type_raw == "ISO":
        famille = "ISO"
    elif interrompu or type_raw in ("IQ", "IVQ", "IUQ"):
        famille = "Q"
        type_q = type_raw[1:] if interrompu else type_raw
    elif type_raw in ("Q", "VQ", "UQ"):
        famille = "Q"
        type_q = type_raw
    elif re.match(r'^(FL|OC|Q|VQ|UQ|ISO|F)', type_raw):
        # Cas avec groupes collés ex: FL(2)
        if re.match(r'^FL', type_raw):
            famille = "FL"
        elif re.match(r'^OC', type_raw):
            famille = "OC"
        elif re.match(r'^(IQ|IVQ|IUQ)', type_raw):
            famille = "Q"
            interrompu = True
            type_q = type_raw[1:]
        else:
            famille = "Q"
            type_q = re.match(r'^(VQ|UQ|Q)', type_raw).group(1)
    else:
        raise ValueError(f"Type de feu non reconnu : '{type_raw}'")

    # Groupes
    groupes = extraire_groupes(type_raw)

    # Période et couleurs dans les tokens suivants
    periode = extraire_periode(tokens[1:])

    couleurs_trouvees = []
    for t in tokens[1:]:
        if re.match(r'^\d', t):
            continue  # période
        if re.match(r'^[WRGBY]+$', t.upper()):
            couleurs_trouvees = extraire_couleurs(t.upper())

    if not couleurs_trouvees:
        couleurs_trouvees = [COULEUR_DEFAUT]

    # Génération de la séquence
    if famille == "F":
        seq = sequence_fixe(periode)
    elif famille == "FL":
        seq = sequence_eclat(groupes, periode)
    elif famille == "OC":
        seq = sequence_occultation(groupes, periode)
    elif famille == "ISO":
        seq = sequence_isophase(periode)
    elif famille == "Q":
        seq = sequence_scintillement(type_q or "Q", groupes, periode, interrompu)
    else:
        seq = sequence_fixe(periode)

    return {
        "couleurs":       couleurs_trouvees,
        "sequence_base":  seq,
        "periode":        sum(s["duree"] for s in seq),
        "famille":        famille,
        "code_original":  code,
    }

def parse(code_complet: str) -> list:
    """
    Parse un code AISM complet et retourne une liste de secteurs.

    Cas 1 — Code unique multi-couleur : 'Fl(2) WRG 10s'
        → 3 secteurs avec la même séquence, couleurs différentes

    Cas 2 — Codes par secteur séparés par '/' : 'F W / Fl R 5s / Q G'
        → 3 secteurs avec séquences ET couleurs différentes

    Retourne : liste de dicts secteur (voir make_secteur)
    """
    code_complet = code_complet.strip()

    # Détection multi-secteurs
    if '/' in code_complet:
        sous_codes = [s.strip() for s in code_complet.split('/')]
        secteurs = []
        for sc in sous_codes:
            parsed = parse_code_simple(sc)
            for couleur in parsed["couleurs"]:
                secteurs.append(make_secteur(couleur, parsed["sequence_base"], famille=parsed["famille"]))
        return secteurs
    else:
        parsed = parse_code_simple(code_complet)
        secteurs = []
        for couleur in parsed["couleurs"]:
            secteurs.append(make_secteur(couleur, parsed["sequence_base"], famille=parsed["famille"]))
        return secteurs

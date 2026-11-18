# tests/test_parser.py — Tests du décodage des codes AISM

import pytest

from parser import parse, parse_code_simple


EXEMPLES = [
    "F W",
    "Fl W 10s",
    "Fl R 5s",
    "Fl(2) W 10s",
    "Fl(3) WRG 15s",
    "Fl(2+1) W 15s",
    "Oc W 4s",
    "Oc(2) R 10s",
    "Iso W 4s",
    "Q G",
    "VQ W",
    "Q(3) W 10s",
    "IQ R 15s",
    "F W / Fl R 5s / Q G",
    "Fl(2) WRG 10s",
]


# ---------------------------------------------------------------------------
# Exemples du README
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("code", EXEMPLES)
def test_exemples_readme_parsent(code):
    secteurs = parse(code)
    assert len(secteurs) >= 1
    for s in secteurs:
        assert s["sequence"], f"séquence vide pour {code!r}"
        assert s["periode"] > 0
        assert s["famille"] in ("F", "FL", "OC", "ISO", "Q")
        assert s["hex"].startswith("#")


@pytest.mark.parametrize("code", EXEMPLES)
def test_periode_coherenteAvecSequence(code):
    for s in parse(code):
        assert round(sum(step["duree"] for step in s["sequence"]), 4) == round(s["periode"], 4)


# ---------------------------------------------------------------------------
# Familles
# ---------------------------------------------------------------------------

def test_feu_fixe():
    secteurs = parse("F W")
    assert len(secteurs) == 1
    s = secteurs[0]
    assert s["famille"] == "F"
    assert s["sequence"] == [{"etat": "on", "duree": 4.0}]
    assert s["periode"] == 4.0


def test_fl_simple_structure():
    s = parse("Fl R 5s")[0]
    assert s["famille"] == "FL"
    assert s["periode"] == 5.0
    assert s["sequence"] == [
        {"etat": "on",  "duree": 0.5},
        {"etat": "off", "duree": 4.5},
    ]


def test_fl_compose_2_plus_1():
    s = parse("Fl(2+1) R 15s")[0]
    assert s["famille"] == "FL"
    assert s["sequence"] == [
        {"etat": "on",  "duree": 0.5},   # éclat
        {"etat": "off", "duree": 0.5},   # inter-éclat
        {"etat": "on",  "duree": 0.5},   # éclat
        {"etat": "off", "duree": 1.0},   # inter-groupe
        {"etat": "on",  "duree": 0.5},   # éclat
        {"etat": "off", "duree": 12.0},  # silence final
    ]
    assert s["periode"] == 15.0


def test_fl_groupe_2():
    s = parse("Fl(2) W 10s")[0]
    assert s["famille"] == "FL"
    assert s["sequence"] == [
        {"etat": "on",  "duree": 0.5},
        {"etat": "off", "duree": 0.5},
        {"etat": "on",  "duree": 0.5},
        {"etat": "off", "duree": 8.5},
    ]


def test_isophase_demi_periodes():
    s = parse("Iso W 4s")[0]
    assert s["famille"] == "ISO"
    assert s["sequence"] == [
        {"etat": "on",  "duree": 2.0},
        {"etat": "off", "duree": 2.0},
    ]


def test_occultation_lumiere_dominante():
    s = parse("Oc W 4s")[0]
    assert s["famille"] == "OC"
    duree_on = sum(step["duree"] for step in s["sequence"] if step["etat"] == "on")
    duree_off = sum(step["duree"] for step in s["sequence"] if step["etat"] == "off")
    assert duree_on > duree_off
    assert duree_off == 0.5
    assert s["periode"] == 4.0
    assert s["sequence"][0]["etat"] == "on"


def test_occultations_groupees():
    s = parse("Oc(2) R 10s")[0]
    assert s["famille"] == "OC"
    off_durees = [step["duree"] for step in s["sequence"] if step["etat"] == "off"]
    assert off_durees == [0.5, 0.5]


# ---------------------------------------------------------------------------
# Scintillements
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("code, periode_eclat", [
    ("Q G", 1.2),
    ("VQ W", 0.5),
])
def test_scintillement_continu(code, periode_eclat):
    s = parse(code)[0]
    assert s["famille"] == "Q"
    assert s["periode"] == pytest.approx(10 * periode_eclat)
    nb_on = sum(1 for step in s["sequence"] if step["etat"] == "on")
    assert nb_on == 10
    for step in s["sequence"]:
        assert step["duree"] == pytest.approx(periode_eclat / 2)


def test_scintillement_groupe():
    s = parse("Q(3) W 10s")[0]
    assert s["sequence"] == [
        {"etat": "on",  "duree": 0.6},
        {"etat": "off", "duree": 0.6},
    ] * 3 + [{"etat": "off", "duree": round(10.0 - 3 * 1.2, 4)}]
    assert s["periode"] == 10.0


def test_scintillement_interrompu_defaut_6_eclats():
    s = parse("IQ R 15s")[0]
    assert s["famille"] == "Q"
    assert s["periode"] == 15.0
    nb_on = sum(1 for step in s["sequence"] if step["etat"] == "on")
    assert nb_on == 6
    silence = s["sequence"][-1]
    assert silence["etat"] == "off"
    assert silence["duree"] == pytest.approx(15.0 - 6 * 1.2)


# ---------------------------------------------------------------------------
# Multi-secteurs
# ---------------------------------------------------------------------------

def test_multi_couleur_meme_cadence():
    secteurs = parse("Fl(3) WRG 15s")
    assert len(secteurs) == 3
    assert [s["couleur"] for s in secteurs] == ["W", "R", "G"]
    assert [s["label"] for s in secteurs] == ["Blanc", "Rouge", "Vert"]
    sequences = [tuple((st["etat"], st["duree"]) for st in s["sequence"]) for s in secteurs]
    assert sequences[0] == sequences[1] == sequences[2]
    assert all(s["periode"] == 15.0 for s in secteurs)


def test_multi_secteurs_heterogenes():
    secteurs = parse("F W / Fl R 5s / Q G")
    assert len(secteurs) == 3
    assert [s["famille"] for s in secteurs] == ["F", "FL", "Q"]
    assert [round(s["periode"], 2) for s in secteurs] == [4.0, 5.0, 12.0]
    assert [s["couleur"] for s in secteurs] == ["W", "R", "G"]


# ---------------------------------------------------------------------------
# Couleurs par défaut et cas limites
# ---------------------------------------------------------------------------

def test_sans_couleur_defaut_blanc():
    s = parse("Iso 4s")[0]
    assert s["couleur"] == "W"
    assert s["label"] == "Blanc"


def test_periode_decimale():
    s = parse("Fl W 2.5s")[0]
    assert s["periode"] == 2.5


def test_casse_insensible():
    s = parse("fl(2) w 10s")[0]
    assert s["famille"] == "FL"
    assert s["periode"] == 10.0


# ---------------------------------------------------------------------------
# Erreurs
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("code", ["", "   ", "code invalide", "XX W 10s"])
def test_codes_invalides_levent_valueerror(code):
    with pytest.raises(ValueError):
        parse(code)


def test_parse_code_simple_retourne_metadonnees():
    parsed = parse_code_simple("Fl(2) W 10s")
    assert parsed["famille"] == "FL"
    assert parsed["couleurs"] == ["W"]
    assert parsed["code_original"] == "Fl(2) W 10s"
    assert parsed["periode"] == 10.0

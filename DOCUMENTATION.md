# Visualiseur de phares AISM — Documentation du projet

## Contexte

Ce projet est né d'un besoin personnel : reproduire des phares en miniature avec les bonnes couleurs et les bonnes cadences lumineuses, pour piloter ensuite des LEDs via des composants discrets (NE555, CD4017) ou un microcontrôleur (ATtiny85).

L'outil permet de saisir un code AISM/IALA (ex : `Fl(2+1) R 15s`) et d'obtenir immédiatement :

- un **diagramme temporel** fidèle à la norme
- des **voyants animés** en temps réel, un par secteur de couleur
- un **panneau de décodage normatif** qui détaille chaque pas de la séquence

---

## Rappel sur les codes AISM

La signalisation maritime internationale (AISM / IALA) décrit les feux par un code normalisé :

```
[Type][Groupes] [Couleur(s)] [Période]
Fl(2+1)          R            15s
```

### Familles de feux

| Code | Famille | Définition |
|---|---|---|
| `F` | Fixe | Lumière constante, pas de clignotement |
| `Fl` | Éclat | Obscurité dominante, éclats brefs |
| `Oc` | Occultation | Lumière dominante, extinctions brèves |
| `Iso` | Isophase | 50% allumé / 50% éteint |
| `Q` | Scintillement | ≥ 50 éclats/min |
| `VQ` | Scintillement rapide | 120 éclats/min |
| `UQ` | Scintillement ultra-rapide | 240 éclats/min |
| `IQ` | Scintillement interrompu | Groupe de scintillements + longue pause |

### Durées normées AISM

| Paramètre | Durée |
|---|---|
| Éclat | 0.5 s |
| Inter-éclat (dans un groupe) | 0.5 s |
| Inter-groupe | 1.0 s |
| Occultation brève | 0.5 s |
| Période éclat Q (50/min) | 1.20 s |
| Période éclat VQ (120/min) | 0.50 s |
| Période éclat UQ (240/min) | 0.25 s |

### Couleurs

| Code | Couleur |
|---|---|
| `W` | Blanc |
| `R` | Rouge |
| `G` | Vert |
| `Y` | Jaune |
| `B` | Bleu |

### Syntaxes supportées

**Code unique multi-couleur** — même cadence, secteurs de couleur différents :

```
Fl(3) WRG 15s
```

**Codes multi-secteurs hétérogènes** — cadences ET couleurs différentes, séparés par `/` :

```
F W / Fl R 5s / Q G
```

---

## Architecture du projet

```
phare_visualiseur/
├── main.py           — Fenêtre principale tkinter, orchestration
├── parser.py         — Décodage du code AISM → séquences temporelles
├── aism.py           — Constantes normées AISM
├── DOCUMENTATION.md  — Ce fichier
└── ui/
    ├── __init__.py
    ├── voyants.py    — Voyants animés en temps réel
    ├── diagramme.py  — Diagramme temporel matplotlib
    └── decodage.py   — Panneau de décodage normatif
```

---

## Description des modules

### `aism.py`

Centralise toutes les constantes normées. C'est le seul fichier à modifier si une valeur normative évolue.

Contient :
- Durées standards (éclat, inter-éclat, inter-groupe, occultation)
- Fréquences de scintillement (Q, VQ, UQ) et calcul de la période associée
- Dictionnaire des couleurs avec les codes hexadécimaux RGB et les labels français
- Constante `N_CYCLES` : nombre de cycles du secteur le plus long affiché sur le diagramme (défaut : 3)

### `parser.py`

Transforme un code AISM textuel en une liste de **secteurs**, chaque secteur étant un dictionnaire contenant :

```python
{
    "couleur":  "R",
    "hex":      "#FF2200",
    "label":    "Rouge",
    "sequence": [
        {"etat": "on",  "duree": 0.5},
        {"etat": "off", "duree": 0.5},
        ...
    ],
    "periode":  15.0,
    "famille":  "FL",
}
```

**Étapes du parsing :**

1. Détection de la syntaxe multi-secteurs (présence de `/`)
2. Pour chaque sous-code : identification de la famille, extraction des groupes, de la période, et des couleurs
3. Génération de la séquence temporelle via les générateurs de chaque famille
4. Calcul du silence final pour caler exactement sur la période déclarée

**Générateurs de séquences :**

| Famille | Logique |
|---|---|
| `F` | Un seul pas ON de durée = période |
| `FL` | Boucle sur les groupes (éclat + inter-éclat), silence inter-groupe entre groupes, silence final |
| `OC` | Lumière initiale, occultations avec lumières intermédiaires, lumière finale |
| `ISO` | Deux pas : ON = période/2, OFF = période/2 |
| `Q` | Boucle de demi-périodes ON/OFF à la fréquence normée, silence final si groupé/interrompu |

### `ui/voyants.py`

Chaque secteur est représenté par un **voyant** : un cercle tkinter animé en temps réel.

L'animation repose sur `after()` — pas de thread, pas de boucle bloquante. Chaque voyant avance indépendamment dans sa propre séquence et se reprogramme à la fin de chaque pas. Les voyants de tous les secteurs démarrent de façon synchronisée.

Quand le voyant est allumé, un halo extérieur apparaît pour renforcer l'effet lumineux. Le label de couleur/secteur est affiché en dessous.

### `ui/diagramme.py`

Génère un diagramme temporel matplotlib embarqué dans la fenêtre tkinter via `FigureCanvasTkAgg`.

**Durée affichée :**  N cycles du secteur de **période maximale**. Les autres secteurs sont affichés sur le même intervalle de temps, ce qui permet de visualiser les déphasages entre secteurs hétérogènes.

Un subplot par secteur, axe X partagé. Des tirets verticaux marquent les frontières de chaque cycle.

### `ui/decodage.py`

Panneau rétractable (clic sur l'en-tête `▼`/`▶`) affiché entre la barre de saisie et les voyants.

**Contenu du panneau :**

- Nom de la famille et définition normative
- En cas de cadence commune : un seul bloc de séquence avec la liste des secteurs
- En cas de cadences hétérogènes : un sous-bloc par secteur, coloré selon sa couleur
- Pour chaque pas de la séquence : état (ON/OFF), durée exacte, annotation du rôle normatif
- Tableau de rappel de toutes les durées normées AISM en bas du panneau

Le panneau est scrollable si son contenu dépasse 220 px.

### `main.py`

Fenêtre principale `tk.Tk`. Contient :

- Barre de saisie avec champ texte et bouton "Afficher" (ou touche Entrée)
- Liste déroulante de 15 exemples couvrant toutes les familles
- Label de résumé (périodes par secteur, ou message d'erreur)
- Instanciation et orchestration des trois panneaux : décodage, voyants, diagramme

---

## Interface utilisateur

```
┌─────────────────────────────────────────────────────────────┐
│  Code AISM : [Fl(2+1) R 15s      ]  [Afficher]             │
│  Exemples : [Éclats composés (2+1) 15s  →  Fl(2+1) W 15s ▼]│
├─────────────────────────────────────────────────────────────┤
│  ✓  Fl(2+1) R 15s  →  Rouge T=15.0s                        │
├─────────────────────────────────────────────────────────────┤
│  ▼  Décodage normatif AISM                                  │
│  Code    : Fl(2+1) R 15s                                   │
│  Famille : Feu à éclats                                     │
│  Secteurs : Rouge  |  T = 15.00s                            │
│  ├─ ON    0.500s  ← éclat           (norme AISM : 0.5s)    │
│  ├─ OFF   0.500s  ← inter-éclat     (norme AISM : 0.5s)    │
│  ├─ ON    0.500s  ← éclat           (norme AISM : 0.5s)    │
│  ├─ OFF   1.000s  ← inter-groupe    (norme AISM : 1.0s)    │
│  ├─ ON    0.500s  ← éclat           (norme AISM : 0.5s)    │
│  └─ OFF  12.000s  ← silence final   (calage période)       │
│  Rappel durées normées AISM ...                             │
├─────────────────────────────────────────────────────────────┤
│    ●                                                        │
│  Rouge                                                      │
├─────────────────────────────────────────────────────────────┤
│  Diagramme temporel (3 cycles × 15s = 45s)                 │
│  Rouge ▁▁███▁███▁██▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁███▁███▁██▁▁▁▁▁...      │
└─────────────────────────────────────────────────────────────┘
```

---

## Dépendances

```bash
pip install matplotlib
```

Tkinter est inclus dans la distribution standard de Python (Windows, macOS). Sous Linux :

```bash
sudo apt install python3-tk
```

---

## Lancement

```bash
cd phare_visualiseur
python main.py
```

---

## Exemples de codes testés

| Code | Description |
|---|---|
| `F W` | Feu fixe blanc |
| `Fl W 10s` | Éclat simple blanc, période 10 s |
| `Fl R 5s` | Éclat rouge, période 5 s |
| `Fl(2) W 10s` | Groupe de 2 éclats blancs, période 10 s |
| `Fl(3) WRG 15s` | 3 éclats, 3 secteurs blanc/rouge/vert, période 15 s |
| `Fl(2+1) W 15s` | Éclats composés : groupe de 2 + groupe de 1, période 15 s |
| `Fl(2+1) R 15s` | Phare de la Pointe des Corbeaux (Île d'Yeu) |
| `Oc W 4s` | Occultation simple blanche, période 4 s |
| `Oc(2) R 10s` | 2 occultations rouges, période 10 s |
| `Iso W 4s` | Isophase blanc, période 4 s |
| `Q G` | Scintillement vert (50 éclats/min) |
| `VQ W` | Scintillement rapide blanc (120 éclats/min) |
| `Q(3) W 10s` | Scintillement groupé par 3, période 10 s |
| `IQ R 15s` | Scintillement interrompu rouge, période 15 s |
| `F W / Fl R 5s / Q G` | Multi-secteurs hétérogènes : 3 cadences différentes |
| `Fl(2) WRG 10s` | Multi-secteurs, cadence commune, 3 couleurs |

---

## Application à l'électronique

Ce visualiseur est conçu pour préparer la réalisation des phares en miniature. Une fois la cadence identifiée et vérifiée visuellement, deux pistes de réalisation :

### Composants discrets

| Besoin | Composants |
|---|---|
| Éclat simple / occultation | NE555 en mode astable |
| Groupes d'éclats | NE555 + CD4017 (compteur décimal) |
| Scintillement | NE555 rapide (≥ 50 Hz) |

Formule de la fréquence NE555 astable :

```
f = 1.44 / ((R1 + 2×R2) × C)
```

Le rapport cyclique (durée ON / période) se règle par le ratio R1/R2.

### Microcontrôleur

Pour les cadences complexes (Fl(2+1), multi-groupes), un **ATtiny85** suffit largement :

- Code figé, pas de mise à jour prévue → une programmation ISP unique
- Consommation très faible, compatible alimentation pile
- La séquence se traduit directement en `digitalWrite` + `delay`

---

## Évolutions possibles

- Export de la séquence au format CSV ou JSON (pour génération de code C/Arduino directement)
- Affichage de la portée nominale et de la hauteur focale si renseignées
- Mode "comparaison" pour afficher deux codes côte à côte
- Calcul automatique des valeurs R1/R2/C pour un NE555 selon la cadence

---

## Références

- **AISM / IALA** — Système mondial d'aides à la navigation maritime
- **SHOM ouvrage 966** — Feux des côtes françaises (référentiel officiel)
- **Base Mérimée** — Fiche du phare de la Pointe des Corbeaux : `IA85000527`
- **Phare de la Pointe des Corbeaux** — `Fl(2+1) R 15s`, portée 18.5 milles, hauteur focale 25.9 m, île d'Yeu (Vendée)

//! rendu.rs — Décodage normatif textuel et diagramme temporel ASCII

use crate::aism::{self, N_CYCLES};
use crate::parser::{Etat, Famille, Secteur, Step};

const LARGEUR_DIAGRAMME: usize = 72;

// ---------------------------------------------------------------------------
// Descriptions normatives des familles
// ---------------------------------------------------------------------------

pub fn description_famille(famille: Famille) -> (&'static str, String) {
    match famille {
        Famille::Fixe => (
            "Feu fixe",
            "Le feu est allumé en permanence et de façon constante.".to_string(),
        ),
        Famille::Eclats => (
            "Feu à éclats",
            format!(
                "La durée de lumière est strictement inférieure à la durée d'obscurité.\n\
                 Chaque éclat dure {}.{}s. L'inter-éclat (dans un groupe) dure {}.{}s.\n\
                 L'inter-groupe dure {}.{}s. Le silence final cale la période déclarée.",
                entier(aism::DUREE_ECLAT), decimal(aism::DUREE_ECLAT),
                entier(aism::DUREE_INTER_ECLAT), decimal(aism::DUREE_INTER_ECLAT),
                entier(aism::DUREE_INTER_GROUPE), decimal(aism::DUREE_INTER_GROUPE)
            ),
        ),
        Famille::Occultation => (
            "Feu à occultations",
            format!(
                "La durée de lumière est strictement supérieure à la durée d'obscurité.\n\
                 Chaque occultation (extinction) dure {}.{}s. Le feu reste allumé le reste du temps.",
                entier(aism::DUREE_OCCULTATION), decimal(aism::DUREE_OCCULTATION)
            ),
        ),
        Famille::Isophase => (
            "Feu isophase",
            "Durée de lumière égale à la durée d'obscurité : 50% / 50% de la période.".to_string(),
        ),
        Famille::Scintillement => (
            "Feu à scintillement",
            "Succession rapide d'éclats à fréquence normée :\n  \
                 Q  (Quick)       : 50 éclats/min  → période éclat = 1.20s\n  \
                 VQ (Very Quick)  : 120 éclats/min → période éclat = 0.50s\n  \
                 UQ (Ultra Quick) : 240 éclats/min → période éclat = 0.25s\n\
                 Interrompu (IQ, IVQ) : groupe de scintillements suivi d'une longue pause."
                .to_string(),
        ),
    }
}

fn entier(d: f64) -> u32 {
    d.trunc() as u32
}

fn decimal(d: f64) -> u32 {
    (d.fract() * 10.0).round() as u32
}

// ---------------------------------------------------------------------------
// Annotation des pas
// ---------------------------------------------------------------------------

fn annote(on: bool, role: &str, duree: Option<f64>, norme: Option<f64>) -> String {
    let etat = if on { "lumière" } else { "obscurité" };
    match norme {
        Some(n) => format!(
            "{} ({}, norme AISM : {:.1}s, durée : {:.3}s)",
            etat, role, n, duree.unwrap_or(0.0)
        ),
        None => format!("{} ({})", etat, role),
    }
}

pub fn annoter_sequence(sequence: &[Step], famille: Famille) -> Vec<String> {
    let n = sequence.len();
    let mut annotations = Vec::with_capacity(n);

    match famille {
        Famille::Fixe => {
            for _ in sequence {
                annotations.push(annote(true, "feu fixe, allumé en permanence", None, None));
            }
        }
        Famille::Isophase => {
            for step in sequence {
                let role = if step.etat == Etat::On {
                    "50% de la période"
                } else {
                    "50% de la période"
                };
                annotations.push(annote(step.etat == Etat::On, role, Some(step.duree), None));
            }
        }
        Famille::Scintillement => {
            for (i, step) in sequence.iter().enumerate() {
                if step.etat == Etat::On {
                    annotations.push(annote(true, "demi-période ON, scintillement", Some(step.duree), None));
                } else if i == n - 1 && step.duree > aism::DUREE_INTER_ECLAT * 2.0 {
                    annotations.push(annote(false, "silence final, calage période", Some(step.duree), None));
                } else {
                    annotations.push(annote(false, "demi-période OFF, scintillement", Some(step.duree), None));
                }
            }
        }
        Famille::Occultation => {
            for step in sequence {
                if step.etat == Etat::Off {
                    if (step.duree - aism::DUREE_OCCULTATION).abs() < 0.05 {
                        annotations.push(annote(false, "occultation", Some(step.duree), Some(aism::DUREE_OCCULTATION)));
                    } else if (step.duree - aism::DUREE_INTER_ECLAT).abs() < 0.05 {
                        annotations.push(annote(false, "inter-occultation", Some(step.duree), Some(aism::DUREE_INTER_ECLAT)));
                    } else {
                        annotations.push(annote(false, "obscurité résiduelle", Some(step.duree), None));
                    }
                } else {
                    annotations.push(annote(true, "hors occultation", Some(step.duree), None));
                }
            }
        }
        Famille::Eclats => {
            for step in sequence {
                if step.etat == Etat::On {
                    annotations.push(annote(true, "éclat", Some(step.duree), Some(aism::DUREE_ECLAT)));
                } else if (step.duree - aism::DUREE_INTER_ECLAT).abs() < 0.05 {
                    annotations.push(annote(false, "inter-éclat", Some(step.duree), Some(aism::DUREE_INTER_ECLAT)));
                } else if (step.duree - aism::DUREE_INTER_GROUPE).abs() < 0.05 {
                    annotations.push(annote(false, "inter-groupe", Some(step.duree), Some(aism::DUREE_INTER_GROUPE)));
                } else {
                    annotations.push(annote(false, "silence final, calage période", Some(step.duree), None));
                }
            }
        }
    }

    annotations
}

// ---------------------------------------------------------------------------
// Diagramme temporel ASCII
// ---------------------------------------------------------------------------

fn etat_a_instant(sequence: &[Step], periode: f64, t: f64) -> bool {
    let mut t = t % periode;
    for step in sequence {
        if t < step.duree {
            return step.etat == Etat::On;
        }
        t -= step.duree;
    }
    false
}

pub fn diagramme_ascii(secteurs: &[Secteur]) -> String {
    let mut out = String::new();
    if secteurs.is_empty() {
        return out;
    }

    let periode_max = secteurs.iter().map(|s| s.periode).fold(f64::MIN, f64::max);
    let duree_totale = periode_max * N_CYCLES as f64;

    out.push_str(&format!(
        "\nDiagramme temporel ({} cycles × {:.1}s = {:.1}s)\n",
        N_CYCLES, periode_max, duree_totale
    ));

    for secteur in secteurs {
        let n_cy = ((duree_totale / secteur.periode).round() as usize).max(1);
        let mut ligne = String::new();
        for i in 0..LARGEUR_DIAGRAMME {
            let t = (i as f64 + 0.5) * duree_totale / LARGEUR_DIAGRAMME as f64;
            if etat_a_instant(&secteur.sequence, secteur.periode, t) {
                ligne.push('█');
            } else {
                ligne.push('·');
            }
        }
        out.push_str(&format!(
            "{:<14} {}   ({}, T = {:.2}s, {} cycle(s))\n",
            secteur.label, ligne, secteur.hex, secteur.periode, n_cy
        ));
    }

    out
}

// ---------------------------------------------------------------------------
// Rapport complet
// ---------------------------------------------------------------------------

pub fn rapport(secteurs: &[Secteur], code_original: &str) -> String {
    let mut out = String::new();

    let resume: Vec<String> = secteurs
        .iter()
        .map(|s| format!("{} T={:.1}s", s.label, s.periode))
        .collect();
    out.push_str(&format!("✓  {}   →   {}\n", code_original, resume.join("  |  ")));

    let (nom, desc) = description_famille(secteurs[0].famille);
    out.push_str(&format!("\nCode    : {}\n", code_original));
    out.push_str(&format!("Famille : {}\n{}\n", nom, desc));

    let sequences_identiques = secteurs
        .windows(2)
        .all(|w| w[0].sequence == w[1].sequence);

    out.push_str("\n");
    if sequences_identiques {
        let couleurs: Vec<String> = secteurs.iter().map(|s| s.label.clone()).collect();
        out.push_str(&format!(
            "Secteurs : {}  |  T = {:.2}s  (cadence identique sur tous les secteurs)\n",
            couleurs.join(" / "),
            secteurs[0].periode
        ));
        out.push_str(&afficher_sequence(&secteurs[0].sequence, secteurs[0].famille));
    } else {
        for (i, sec) in secteurs.iter().enumerate() {
            out.push_str(&format!(
                "Secteur {} — {}  |  T = {:.2}s\n",
                i + 1,
                sec.label,
                sec.periode
            ));
            out.push_str(&afficher_sequence(&sec.sequence, sec.famille));
            if i < secteurs.len() - 1 {
                out.push_str("\n");
            }
        }
    }

    out.push_str("\nRappel des durées normées AISM\n");
    out.push_str(&format!("  Éclat                : {:.1}s\n", aism::DUREE_ECLAT));
    out.push_str(&format!("  Inter-éclat          : {:.1}s\n", aism::DUREE_INTER_ECLAT));
    out.push_str(&format!("  Inter-groupe         : {:.1}s\n", aism::DUREE_INTER_GROUPE));
    out.push_str(&format!("  Occultation brève    : {:.1}s\n", aism::DUREE_OCCULTATION));
    out.push_str(&format!("  Scintillement Q      : {:.2}s / éclat  (50 éclats/min)\n", 60.0 / 50.0));
    out.push_str(&format!("  Scintillement VQ     : {:.2}s / éclat  (120 éclats/min)\n", 60.0 / 120.0));
    out.push_str(&format!("  Scintillement UQ     : {:.3}s / éclat  (240 éclats/min)\n", 60.0 / 240.0));
    out.push_str(&format!("  Diagramme : {} cycles du secteur de période max\n", N_CYCLES));

    out.push_str(&diagramme_ascii(secteurs));

    out
}

pub fn afficher_sequence(sequence: &[Step], famille: Famille) -> String {
    let annotations = annoter_sequence(sequence, famille);
    let n = annotations.len();
    let mut out = String::new();

    for (i, (step, annotation)) in sequence.iter().zip(annotations).enumerate() {
        let branche = if i == n - 1 { "└─" } else { "├─" };
        let etat_str = if step.etat == Etat::On { "ON " } else { "OFF" };
        out.push_str(&format!(
            "  {} {:>3} {:>8.3}s  ←  {}\n",
            branche, etat_str, step.duree, annotation
        ));
    }

    out
}

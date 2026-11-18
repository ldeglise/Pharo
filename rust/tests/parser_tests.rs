// tests/parser_tests.rs — Portage des tests pytest de tests/test_parser.py

use pharo::aism::{
    DUREE_ECLAT, DUREE_INTER_ECLAT, DUREE_INTER_GROUPE, DUREE_OCCULTATION,
    N_CYCLES, NB_ECLATS_IQ_DEFAUT,
};
use pharo::parser::{parse, parse_code_simple, Etat, Famille, Step};

fn approx(a: f64, b: f64) {
    assert!(
        (a - b).abs() < 1e-9,
        "valeurs différentes : {} vs {}",
        a,
        b
    );
}

fn step(etat: Etat, duree: f64) -> Step {
    Step { etat, duree }
}

fn on(d: f64) -> Step {
    step(Etat::On, d)
}

fn off(d: f64) -> Step {
    step(Etat::Off, d)
}

// ---------------------------------------------------------------------------
// Exemples du README
// ---------------------------------------------------------------------------

const EXEMPLES: &[&str] = &[
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
];

#[test]
fn exemples_readme_parsent() {
    for &code in EXEMPLES {
        let secteurs = parse(code).unwrap_or_else(|e| panic!("échec sur {:?} : {}", code, e));
        assert!(!secteurs.is_empty(), "aucun secteur pour {:?}", code);
        for s in &secteurs {
            assert!(!s.sequence.is_empty(), "séquence vide pour {:?}", code);
            assert!(s.periode > 0.0);
            assert!(s.hex.starts_with('#'));
        }
    }
}

#[test]
fn periode_coherente_avec_sequence() {
    for &code in EXEMPLES {
        for s in parse(code).unwrap() {
            let somme: f64 = s.sequence.iter().map(|st| st.duree).sum();
            approx(somme, s.periode);
        }
    }
}

// ---------------------------------------------------------------------------
// Familles
// ---------------------------------------------------------------------------

#[test]
fn feu_fixe() {
    let secteurs = parse("F W").unwrap();
    assert_eq!(secteurs.len(), 1);
    let s = &secteurs[0];
    assert_eq!(s.famille, Famille::Fixe);
    assert_eq!(s.sequence, vec![on(4.0)]);
    approx(s.periode, 4.0);
}

#[test]
fn fl_simple_structure() {
    let s = &parse("Fl R 5s").unwrap()[0];
    assert_eq!(s.famille, Famille::Eclats);
    approx(s.periode, 5.0);
    assert_eq!(
        s.sequence,
        vec![on(DUREE_ECLAT), off(4.5)]
    );
}

#[test]
fn fl_compose_2_plus_1() {
    let s = &parse("Fl(2+1) R 15s").unwrap()[0];
    assert_eq!(s.famille, Famille::Eclats);
    assert_eq!(
        s.sequence,
        vec![
            on(0.5),   // éclat
            off(0.5),  // inter-éclat
            on(0.5),   // éclat
            off(1.0),  // inter-groupe
            on(0.5),   // éclat
            off(12.0), // silence final
        ]
    );
    approx(s.periode, 15.0);
}

#[test]
fn fl_groupe_2() {
    let s = &parse("Fl(2) W 10s").unwrap()[0];
    assert_eq!(s.famille, Famille::Eclats);
    assert_eq!(
        s.sequence,
        vec![on(0.5), off(0.5), on(0.5), off(8.5)]
    );
}

#[test]
fn isophase_demi_periodes() {
    let s = &parse("Iso W 4s").unwrap()[0];
    assert_eq!(s.famille, Famille::Isophase);
    assert_eq!(s.sequence, vec![on(2.0), off(2.0)]);
}

#[test]
fn occultation_lumiere_dominante() {
    let s = &parse("Oc W 4s").unwrap()[0];
    assert_eq!(s.famille, Famille::Occultation);
    let duree_on: f64 = s.sequence.iter().filter(|st| st.etat == Etat::On).map(|st| st.duree).sum();
    let duree_off: f64 = s.sequence.iter().filter(|st| st.etat == Etat::Off).map(|st| st.duree).sum();
    assert!(duree_on > duree_off);
    approx(duree_off, 0.5);
    approx(s.periode, 4.0);
    assert_eq!(s.sequence[0].etat, Etat::On);
}

#[test]
fn occultations_groupees() {
    let s = &parse("Oc(2) R 10s").unwrap()[0];
    assert_eq!(s.famille, Famille::Occultation);
    let off_durees: Vec<f64> = s
        .sequence
        .iter()
        .filter(|st| st.etat == Etat::Off)
        .map(|st| st.duree)
        .collect();
    assert_eq!(off_durees, vec![DUREE_OCCULTATION, DUREE_OCCULTATION]);
}

// ---------------------------------------------------------------------------
// Scintillements
// ---------------------------------------------------------------------------

#[test]
fn scintillement_continu_q() {
    let s = &parse("Q G").unwrap()[0];
    assert_eq!(s.famille, Famille::Scintillement);
    approx(s.periode, 10.0 * 1.2);
    let nb_on = s.sequence.iter().filter(|st| st.etat == Etat::On).count();
    assert_eq!(nb_on, 10);
    for st in &s.sequence {
        approx(st.duree, 0.6);
    }
}

#[test]
fn scintillement_continu_vq() {
    let s = &parse("VQ W").unwrap()[0];
    assert_eq!(s.famille, Famille::Scintillement);
    approx(s.periode, 10.0 * 0.5);
    for st in &s.sequence {
        approx(st.duree, 0.25);
    }
}

#[test]
fn scintillement_groupe() {
    let silence = 10.0 - 3.0 * 1.2;
    let s = &parse("Q(3) W 10s").unwrap()[0];
    let attendu: Vec<Step> = [on(0.6), off(0.6), on(0.6), off(0.6), on(0.6), off(0.6), off(silence)].to_vec();
    for (st, ref_st) in s.sequence.iter().zip(attendu.iter()) {
        assert_eq!(st.etat, ref_st.etat);
        approx(st.duree, ref_st.duree);
    }
    approx(s.periode, 10.0);
}

#[test]
fn scintillement_interrompu_defaut_6_eclats() {
    let s = &parse("IQ R 15s").unwrap()[0];
    assert_eq!(s.famille, Famille::Scintillement);
    approx(s.periode, 15.0);
    let nb_on = s.sequence.iter().filter(|st| st.etat == Etat::On).count();
    assert_eq!(nb_on, NB_ECLATS_IQ_DEFAUT);
    let silence = s.sequence.last().unwrap();
    assert_eq!(silence.etat, Etat::Off);
    approx(silence.duree, 15.0 - NB_ECLATS_IQ_DEFAUT as f64 * 1.2);
}

#[test]
fn scintillement_interrompu_sans_periode_continu() {
    // IQ sans période : pas de branche interrompue (nécessite une periode),
    // comportement identique au Python
    let s = &parse("IQ R").unwrap()[0];
    assert_eq!(s.famille, Famille::Scintillement);
    assert!(!s.sequence.is_empty());
}

// ---------------------------------------------------------------------------
// Multi-secteurs
// ---------------------------------------------------------------------------

#[test]
fn multi_couleur_meme_cadence() {
    let secteurs = parse("Fl(3) WRG 15s").unwrap();
    assert_eq!(secteurs.len(), 3);
    let couleurs: Vec<char> = secteurs.iter().map(|s| s.couleur).collect();
    assert_eq!(couleurs, vec!['W', 'R', 'G']);
    let labels: Vec<&str> = secteurs.iter().map(|s| s.label.as_str()).collect();
    assert_eq!(labels, vec!["Blanc", "Rouge", "Vert"]);
    let refs: Vec<Vec<(Etat, f64)>> = secteurs
        .iter()
        .map(|s| s.sequence.iter().map(|st| (st.etat, st.duree)).collect())
        .collect();
    assert_eq!(refs[0], refs[1]);
    assert_eq!(refs[1], refs[2]);
    for s in &secteurs {
        approx(s.periode, 15.0);
    }
}

#[test]
fn multi_secteurs_heterogenes() {
    let secteurs = parse("F W / Fl R 5s / Q G").unwrap();
    assert_eq!(secteurs.len(), 3);
    let familles: Vec<Famille> = secteurs.iter().map(|s| s.famille).collect();
    assert_eq!(familles, vec![Famille::Fixe, Famille::Eclats, Famille::Scintillement]);
    let periodes: Vec<u32> = secteurs.iter().map(|s| s.periode.round() as u32).collect();
    assert_eq!(periodes, vec![4, 5, 12]);
    let couleurs: Vec<char> = secteurs.iter().map(|s| s.couleur).collect();
    assert_eq!(couleurs, vec!['W', 'R', 'G']);
}

// ---------------------------------------------------------------------------
// Couleurs par défaut et cas limites
// ---------------------------------------------------------------------------

#[test]
fn sans_couleur_defaut_blanc() {
    let s = &parse("Iso 4s").unwrap()[0];
    assert_eq!(s.couleur, 'W');
    assert_eq!(s.label, "Blanc");
}

#[test]
fn periode_decimale() {
    let s = &parse("Fl W 2.5s").unwrap()[0];
    approx(s.periode, 2.5);
}

#[test]
fn casse_insensible() {
    let s = &parse("fl(2) w 10s").unwrap()[0];
    assert_eq!(s.famille, Famille::Eclats);
    approx(s.periode, 10.0);
}

// ---------------------------------------------------------------------------
// Erreurs
// ---------------------------------------------------------------------------

#[test]
fn codes_invalides_levent_erreur() {
    for code in ["", "   ", "code invalide", "XX W 10s"] {
        assert!(
            parse(code).is_err(),
            "une erreur était attendue pour {:?}",
            code
        );
    }
}

#[test]
fn message_code_vide() {
    let err = parse("").unwrap_err();
    assert_eq!(err, "Code vide : ''");
}

#[test]
fn message_type_non_reconnu() {
    let err = parse("code invalide").unwrap_err();
    assert_eq!(err, "Type de feu non reconnu : 'CODE'");
}

// ---------------------------------------------------------------------------
// Métadonnées
// ---------------------------------------------------------------------------

#[test]
fn parse_code_simple_retourne_metadonnees() {
    let parsed = parse_code_simple("Fl(2) W 10s").unwrap();
    assert_eq!(parsed.famille, Famille::Eclats);
    assert_eq!(parsed.couleurs, vec!['W']);
    assert_eq!(parsed.code_original, "Fl(2) W 10s");
    approx(parsed.periode, 10.0);
}

#[test]
fn const_coherence() {
    approx(DUREE_INTER_ECLAT, 0.5);
    approx(DUREE_INTER_GROUPE, 1.0);
    assert_eq!(N_CYCLES, 3);
}

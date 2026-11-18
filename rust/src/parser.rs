//! parser.rs — Décodage des codes AISM vers séquences temporelles

use crate::aism::{self, couleur, TypeQ};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Etat {
    On,
    Off,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Famille {
    Fixe,
    Eclats,
    Occultation,
    Isophase,
    Scintillement,
}

impl Famille {
    pub fn as_str(self) -> &'static str {
        match self {
            Famille::Fixe => "F",
            Famille::Eclats => "FL",
            Famille::Occultation => "OC",
            Famille::Isophase => "ISO",
            Famille::Scintillement => "Q",
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct Step {
    pub etat: Etat,
    pub duree: f64,
}

pub fn make_step(etat: Etat, duree: f64) -> Step {
    Step { etat, duree: (duree * 10000.0).round() / 10000.0 }
}

#[derive(Debug, Clone)]
pub struct Secteur {
    pub couleur: char,
    pub hex: String,
    #[allow(dead_code)]
    pub fond: String,
    pub label: String,
    pub sequence: Vec<Step>,
    pub periode: f64,
    pub famille: Famille,
}

#[derive(Debug, Clone)]
pub struct CodeSimple {
    pub couleurs: Vec<char>,
    pub sequence_base: Vec<Step>,
    pub periode: f64,
    pub famille: Famille,
    pub code_original: String,
}

pub fn make_secteur(code_couleur: char, sequence: Vec<Step>, famille: Option<Famille>) -> Secteur {
    let info = couleur(code_couleur)
        .or_else(|| couleur(aism::COULEUR_DEFAUT))
        .expect("couleur par défaut toujours définie");
    Secteur {
        couleur: code_couleur,
        hex: info.hex.to_string(),
        fond: info.fond.to_string(),
        label: info.label.to_string(),
        periode: sequence.iter().map(|s| s.duree).sum(),
        sequence,
        famille: famille.unwrap_or(Famille::Eclats),
    }
}

// ---------------------------------------------------------------------------
// Extraction des composantes d'un code simple
// ---------------------------------------------------------------------------

pub fn extraire_couleurs(token: &str) -> Vec<char> {
    let mut couleurs: Vec<char> = token
        .chars()
        .map(|c| c.to_ascii_uppercase())
        .filter(|c| couleur(*c).is_some())
        .collect();
    if couleurs.is_empty() {
        couleurs = vec![aism::COULEUR_DEFAUT];
    }
    couleurs
}

fn parse_duree_prefixe(prefix: &str) -> Option<f64> {
    if prefix.is_empty() {
        return None;
    }
    let mut parts = prefix.split('.');
    let ent = parts.next()?;
    let dec = parts.next();
    if parts.next().is_some() {
        return None;
    }
    if !ent.chars().all(|c| c.is_ascii_digit()) || ent.is_empty() {
        return None;
    }
    if let Some(d) = dec {
        if !d.chars().all(|c| c.is_ascii_digit()) {
            return None;
        }
    }
    prefix.parse::<f64>().ok()
}

pub fn extraire_periode(tokens: &[&str]) -> Option<f64> {
    for t in tokens {
        let lower = t.to_lowercase();
        if let Some(prefix) = lower.strip_suffix('s') {
            if let Some(v) = parse_duree_prefixe(prefix) {
                return Some(v);
            }
        }
    }
    None
}

pub fn extraire_groupes(type_feu: &str) -> Vec<usize> {
    let open = match type_feu.find('(') {
        Some(i) => i,
        None => return vec![1],
    };
    let close = match type_feu[open..].find(')') {
        Some(j) => open + j,
        None => return vec![1],
    };
    let contenu = &type_feu[open + 1..close];
    let parsed: Vec<usize> = contenu
        .split('+')
        .map(|p| p.trim().parse::<usize>())
        .collect::<Result<_, _>>()
        .unwrap_or_default();
    if parsed.is_empty() {
        vec![1]
    } else {
        parsed
    }
}

// ---------------------------------------------------------------------------
// Générateurs de séquences par famille
// ---------------------------------------------------------------------------

pub fn sequence_fixe(periode: Option<f64>) -> Vec<Step> {
    vec![make_step(Etat::On, periode.unwrap_or(4.0))]
}

pub fn sequence_eclat(groupes: &[usize], periode: Option<f64>) -> Vec<Step> {
    let mut seq = Vec::new();
    let mut duree_active = 0.0;

    for (idx_groupe, &nb_eclats) in groupes.iter().enumerate() {
        for i in 0..nb_eclats {
            seq.push(make_step(Etat::On, aism::DUREE_ECLAT));
            duree_active += aism::DUREE_ECLAT;
            if i + 1 < nb_eclats {
                seq.push(make_step(Etat::Off, aism::DUREE_INTER_ECLAT));
                duree_active += aism::DUREE_INTER_ECLAT;
            }
        }
        if idx_groupe + 1 < groupes.len() {
            seq.push(make_step(Etat::Off, aism::DUREE_INTER_GROUPE));
            duree_active += aism::DUREE_INTER_GROUPE;
        }
    }

    match periode {
        Some(p) => {
            let silence_final = p - duree_active;
            if silence_final > 0.0 {
                seq.push(make_step(Etat::Off, silence_final));
            }
        }
        None => seq.push(make_step(Etat::Off, aism::DUREE_INTER_GROUPE * 2.0)),
    }

    seq
}

pub fn sequence_occultation(groupes: &[usize], periode: Option<f64>) -> Vec<Step> {
    let mut seq = Vec::new();
    let mut duree_active = 0.0;
    let nb_oc = groupes.first().copied().unwrap_or(1);

    let duree_obscurite =
        nb_oc as f64 * aism::DUREE_OCCULTATION + (nb_oc as f64 - 1.0) * aism::DUREE_INTER_ECLAT;
    let duree_lumiere = match periode {
        Some(p) => p - duree_obscurite,
        None => nb_oc as f64 * 2.0,
    };

    if duree_lumiere > 0.0 {
        seq.push(make_step(Etat::On, duree_lumiere / 2.0));
        duree_active += duree_lumiere / 2.0;
    }

    for i in 0..nb_oc {
        seq.push(make_step(Etat::Off, aism::DUREE_OCCULTATION));
        duree_active += aism::DUREE_OCCULTATION;
        if i + 1 < nb_oc {
            seq.push(make_step(Etat::On, aism::DUREE_INTER_ECLAT));
            duree_active += aism::DUREE_INTER_ECLAT;
        }
    }

    let reste = match periode {
        Some(p) => p - duree_active,
        None => duree_lumiere / 2.0,
    };
    if reste > 0.0 {
        seq.push(make_step(Etat::On, reste));
    }

    seq
}

pub fn sequence_isophase(periode: Option<f64>) -> Vec<Step> {
    let p = periode.unwrap_or(4.0);
    let demi = p / 2.0;
    vec![make_step(Etat::On, demi), make_step(Etat::Off, demi)]
}

fn groupe_eclats(nb: usize, duree_on: f64, duree_off: f64, periode_eclat: f64, periode: f64) -> Vec<Step> {
    let mut seq = Vec::new();
    let mut duree_active = 0.0;
    for _ in 0..nb {
        seq.push(make_step(Etat::On, duree_on));
        seq.push(make_step(Etat::Off, duree_off));
        duree_active += periode_eclat;
    }
    let silence = periode - duree_active;
    if silence > 0.0 {
        seq.push(make_step(Etat::Off, silence));
    }
    seq
}

pub fn sequence_scintillement(
    type_q: TypeQ,
    groupes: &[usize],
    periode: Option<f64>,
    interrompu: bool,
) -> Vec<Step> {
    let periode_eclat = type_q.periode();
    let duree_on = periode_eclat * 0.5;
    let duree_off = periode_eclat * 0.5;

    if interrompu && periode.is_some() {
        let nb = groupes.first().copied().unwrap_or(1);
        return groupe_eclats(nb, duree_on, duree_off, periode_eclat, periode.unwrap());
    }

    let groupe = groupes.first().copied().unwrap_or(1);
    if groupe > 1 && periode.is_some() {
        return groupe_eclats(groupe, duree_on, duree_off, periode_eclat, periode.unwrap());
    }

    let nb = match periode {
        Some(p) => ((p / periode_eclat) as usize).max(1),
        None => 10,
    };
    let mut seq = Vec::new();
    for _ in 0..nb {
        seq.push(make_step(Etat::On, duree_on));
        seq.push(make_step(Etat::Off, duree_off));
    }
    seq
}

// ---------------------------------------------------------------------------
// Identification du type de feu
// ---------------------------------------------------------------------------

fn type_base(rest: &str) -> Option<&'static str> {
    ["FL", "OC", "ISO", "VQ", "UQ", "Q", "F"]
        .iter()
        .copied()
        .find(|p| rest.starts_with(p))
}

pub fn identifier_type_feu(type_raw: &str) -> Result<(Famille, Option<TypeQ>, bool), String> {
    let t = type_raw.to_uppercase();
    let erreur = || format!("Type de feu non reconnu : '{}'", type_raw);

    if let Some(rest) = t.strip_prefix('I') {
        match rest {
            "Q" => return Ok((Famille::Scintillement, Some(TypeQ::Q), true)),
            "VQ" => return Ok((Famille::Scintillement, Some(TypeQ::VQ), true)),
            "UQ" => return Ok((Famille::Scintillement, Some(TypeQ::UQ), true)),
            _ => {}
        }
    }

    match type_base(&t) {
        Some("F") => Ok((Famille::Fixe, None, false)),
        Some("FL") => Ok((Famille::Eclats, None, false)),
        Some("OC") => Ok((Famille::Occultation, None, false)),
        Some("ISO") => Ok((Famille::Isophase, None, false)),
        Some("Q") => Ok((Famille::Scintillement, Some(TypeQ::Q), false)),
        Some("VQ") => Ok((Famille::Scintillement, Some(TypeQ::VQ), false)),
        Some("UQ") => Ok((Famille::Scintillement, Some(TypeQ::UQ), false)),
        _ => Err(erreur()),
    }
}

// ---------------------------------------------------------------------------
// Parseur d'un code simple (un seul secteur)
// ---------------------------------------------------------------------------

pub fn parse_code_simple(code: &str) -> Result<CodeSimple, String> {
    let code = code.trim();
    if code.is_empty() {
        return Err(format!("Code vide : '{}'", code));
    }
    let tokens: Vec<&str> = code.split_whitespace().collect();

    let type_raw = tokens[0].to_uppercase();
    let (famille, type_q, interrompu) = identifier_type_feu(&type_raw)?;

    let mut groupes = extraire_groupes(&type_raw);
    if famille == Famille::Scintillement && interrompu && !type_raw.contains('(') {
        groupes = vec![aism::NB_ECLATS_IQ_DEFAUT];
    }

    let periode = extraire_periode(&tokens[1..]);

    let mut couleurs_trouvees: Vec<char> = Vec::new();
    for t in &tokens[1..] {
        if t.chars().next().map_or(false, |c| c.is_ascii_digit()) {
            continue;
        }
        let up = t.to_uppercase();
        if !up.is_empty() && up.chars().all(|c| matches!(c, 'W' | 'R' | 'G' | 'B' | 'Y')) {
            couleurs_trouvees = extraire_couleurs(&up);
        }
    }
    if couleurs_trouvees.is_empty() {
        couleurs_trouvees = vec![aism::COULEUR_DEFAUT];
    }

    let sequence_base = match famille {
        Famille::Fixe => sequence_fixe(periode),
        Famille::Eclats => sequence_eclat(&groupes, periode),
        Famille::Occultation => sequence_occultation(&groupes, periode),
        Famille::Isophase => sequence_isophase(periode),
        Famille::Scintillement => {
            sequence_scintillement(type_q.unwrap_or(TypeQ::Q), &groupes, periode, interrompu)
        }
    };

    Ok(CodeSimple {
        periode: sequence_base.iter().map(|s| s.duree).sum(),
        couleurs: couleurs_trouvees,
        sequence_base,
        famille,
        code_original: code.to_string(),
    })
}

// ---------------------------------------------------------------------------
// Parseur d'un code complet (multi-secteurs)
// ---------------------------------------------------------------------------

pub fn parse(code_complet: &str) -> Result<Vec<Secteur>, String> {
    let code_complet = code_complet.trim();

    let mut secteurs = Vec::new();
    for sous_code in code_complet.split('/') {
        let parsed = parse_code_simple(sous_code.trim())?;
        for &c in &parsed.couleurs {
            secteurs.push(make_secteur(c, parsed.sequence_base.clone(), Some(parsed.famille)));
        }
    }
    Ok(secteurs)
}

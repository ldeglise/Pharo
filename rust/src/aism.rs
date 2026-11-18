//! aism.rs — Constantes normées AISM / IALA pour la signalisation maritime

pub const DUREE_ECLAT: f64 = 0.5;
pub const DUREE_INTER_ECLAT: f64 = 0.5;
pub const DUREE_INTER_GROUPE: f64 = 1.0;
pub const DUREE_OCCULTATION: f64 = 0.5;

pub const SCINTILLEMENT_Q: f64 = 50.0;
pub const SCINTILLEMENT_VQ: f64 = 120.0;
pub const SCINTILLEMENT_UQ: f64 = 240.0;

pub const NB_ECLATS_IQ_DEFAUT: usize = 6;

pub const COULEUR_DEFAUT: char = 'W';
pub const ETEINT_HEX: &str = "#1A1A1A";
pub const N_CYCLES: usize = 3;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CouleurInfo {
    pub hex: &'static str,
    pub fond: &'static str,
    pub label: &'static str,
}

pub fn couleur(code: char) -> Option<CouleurInfo> {
    match code.to_ascii_uppercase() {
        'W' => Some(CouleurInfo { hex: "#FFFFFF", fond: "#AAAAAA", label: "Blanc" }),
        'R' => Some(CouleurInfo { hex: "#FF2200", fond: "#330000", label: "Rouge" }),
        'G' => Some(CouleurInfo { hex: "#00CC44", fond: "#003311", label: "Vert" }),
        'Y' => Some(CouleurInfo { hex: "#FFD700", fond: "#332200", label: "Jaune" }),
        'B' => Some(CouleurInfo { hex: "#4488FF", fond: "#001133", label: "Bleu" }),
        _ => None,
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TypeQ {
    Q,
    VQ,
    UQ,
}

impl TypeQ {
    pub fn periode(self) -> f64 {
        match self {
            TypeQ::Q => 60.0 / SCINTILLEMENT_Q,
            TypeQ::VQ => 60.0 / SCINTILLEMENT_VQ,
            TypeQ::UQ => 60.0 / SCINTILLEMENT_UQ,
        }
    }
}

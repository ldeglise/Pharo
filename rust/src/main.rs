//! main.rs — CLI du visualiseur de phares AISM

use std::env;

fn main() {
    let args: Vec<String> = env::args().collect();

    let code = match args.get(1) {
        Some(c) => c.clone(),
        None => {
            eprintln!("Usage : pharo \"<code AISM>\"");
            eprintln!("Exemple : pharo \"Fl(2+1) R 15s\"");
            eprintln!("Multi-secteurs : pharo \"F W / Fl R 5s / Q G\"");
            std::process::exit(2);
        }
    };

    match pharo::parser::parse(&code) {
        Ok(secteurs) if !secteurs.is_empty() => {
            print!("{}", pharo::rendu::rapport(&secteurs, &code));
        }
        Ok(_) => {
            eprintln!("✗ Erreur : aucun secteur parsé");
            std::process::exit(1);
        }
        Err(e) => {
            eprintln!("✗ Erreur : {}", e);
            std::process::exit(1);
        }
    }
}

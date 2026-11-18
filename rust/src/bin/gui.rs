// rust/src/bin/gui.rs — GUI iced du visualiseur de phares AISM
//
// Portage de l'interface tkinter (main.py, ui/voyants.py, ui/diagramme.py,
// ui/decodage.py) sur iced, en réutilisant parser.rs et rendu.rs.

use std::time::{Duration, Instant};

use iced::widget::canvas::{Frame, Geometry, Path, Stroke, Text as CanvasText};
use iced::widget::{button, canvas, column, pick_list, row, scrollable, text, text_input, Canvas};
use iced::{
    time, Alignment, Color, Element, Font, Length, Point, Pixels, Rectangle,
    Size, Subscription, Task, Theme,
};

use pharo::aism::{ETEINT_HEX, N_CYCLES};
use pharo::parser::{parse, Etat, Secteur};
use pharo::rendu::{afficher_sequence, description_famille};

// ---------------------------------------------------------------------------
// Exemples de codes pour la liste déroulante
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq, Eq, Copy)]
struct Exemple {
    label: &'static str,
    code: &'static str,
}

impl std::fmt::Display for Exemple {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}  →  {}", self.label, self.code)
    }
}

const EXEMPLES: &[Exemple] = &[
    Exemple { label: "Feu fixe blanc", code: "F W" },
    Exemple { label: "Éclat simple 10s", code: "Fl W 10s" },
    Exemple { label: "Éclat rouge 5s", code: "Fl R 5s" },
    Exemple { label: "Éclats groupés (2) blanc 10s", code: "Fl(2) W 10s" },
    Exemple { label: "Éclats groupés (3) WRG 15s", code: "Fl(3) WRG 15s" },
    Exemple { label: "Éclats composés (2+1) 15s", code: "Fl(2+1) W 15s" },
    Exemple { label: "Occultation simple blanc 4s", code: "Oc W 4s" },
    Exemple { label: "Occultations groupées (2) R 10s", code: "Oc(2) R 10s" },
    Exemple { label: "Isophase blanc 4s", code: "Iso W 4s" },
    Exemple { label: "Scintillement Q vert", code: "Q G" },
    Exemple { label: "Scintillement rapide VQ blanc", code: "VQ W" },
    Exemple { label: "Scintillement groupé Q(3) 10s", code: "Q(3) W 10s" },
    Exemple { label: "Scintillement interrompu IQ R", code: "IQ R 15s" },
    Exemple { label: "Multi-secteurs hétérogènes", code: "F W / Fl R 5s / Q G" },
    Exemple { label: "Multi-secteurs (2) WRG 10s", code: "Fl(2) WRG 10s" },
];

fn exemples() -> Vec<Exemple> {
    EXEMPLES.to_vec()
}

// ---------------------------------------------------------------------------
// Application
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
enum Message {
    CodeChanged(String),
    ExempleSelected(Exemple),
    Valider,
    Tick,
}

struct AppPhare {
    code: String,
    exemple: Option<Exemple>,
    secteurs: Vec<Secteur>,
    info: String,
    erreur: bool,
    depart: Option<Instant>,
}

impl AppPhare {
    fn nouveau() -> Self {
        let mut app = Self {
            code: EXEMPLES[0].code.to_string(),
            exemple: Some(EXEMPLES[0]),
            secteurs: Vec::new(),
            info: String::new(),
            erreur: false,
            depart: None,
        };
        app.valider();
        app
    }

    fn definir_erreur(&mut self, msg: &str) {
        self.info = format!("✗  Erreur : {}", msg);
        self.erreur = true;
    }

    fn valider(&mut self) {
        if self.code.trim().is_empty() {
            return;
        }
        match parse(&self.code) {
            Ok(secteurs) if !secteurs.is_empty() => {
                let resume: Vec<String> = secteurs
                    .iter()
                    .map(|s| format!("{} T={:.1}s", s.label, s.periode))
                    .collect();
                self.info = format!("✓  {}   →   {}", self.code, resume.join("  |  "));
                self.erreur = false;
                self.depart = Some(Instant::now());
                self.secteurs = secteurs;
            }
            Ok(_) => self.definir_erreur("aucun secteur parsé"),
            Err(e) => self.definir_erreur(&e),
        }
    }
}

fn update(app: &mut AppPhare, message: Message) -> Task<Message> {
    match message {
        Message::CodeChanged(code) => {
            app.code = code;
            app.exemple = None;
        }
        Message::ExempleSelected(ex) => {
            app.code = ex.code.to_string();
            app.exemple = Some(ex);
            app.valider();
        }
        Message::Valider => app.valider(),
        Message::Tick => {}
    }
    Task::none()
}

fn subscription(app: &AppPhare) -> Subscription<Message> {
    if app.secteurs.is_empty() {
        Subscription::none()
    } else {
        time::every(Duration::from_millis(50)).map(|_| Message::Tick)
    }
}

// ---------------------------------------------------------------------------
// Vue
// ---------------------------------------------------------------------------

fn couleur_info(erreur: bool) -> Color {
    if erreur {
        Color::from_rgb8(0xFF, 0x66, 0x44)
    } else {
        Color::from_rgb8(0x66, 0xAA, 0x66)
    }
}

fn couleur_hex(hex: &str) -> Color {
    let v = hex.trim_start_matches('#');
    let r = u8::from_str_radix(&v[0..2], 16).unwrap_or(0);
    let g = u8::from_str_radix(&v[2..4], 16).unwrap_or(0);
    let b = u8::from_str_radix(&v[4..6], 16).unwrap_or(0);
    Color::from_rgb8(r, g, b)
}

fn view(app: &AppPhare) -> Element<'_, Message> {
    let barre = row![
        text("Code AISM :").size(13),
        text_input("Ex : Fl(2+1) R 15s", &app.code)
            .on_input(Message::CodeChanged)
            .on_submit(Message::Valider)
            .width(280)
            .padding(6),
        button("Afficher")
            .padding([5, 14])
            .on_press(Message::Valider),
        text("Exemples :").size(12),
        pick_list(exemples(), app.exemple, Message::ExempleSelected).width(350),
    ]
    .spacing(10)
    .align_y(Alignment::Center)
    .padding(10);

    let info = text(&app.info).size(12).color(couleur_info(app.erreur));

    if app.secteurs.is_empty() {
        return column![barre, info].spacing(6).padding(8).into();
    }

    let mut voyants = row![].spacing(20).padding(10);
    for s in &app.secteurs {
        voyants = voyants.push(
            Canvas::new(VoyantData::nouveau(s, app.depart))
                .width(Length::Fixed(120.0))
                .height(Length::Fixed(120.0)),
        );
    }

    let mut decodage = column![].spacing(3);
    let (nom_famille, desc_famille) = description_famille(app.secteurs[0].famille);
    decodage = decodage.push(text(format!("Code :  {}", app.code)).size(13));
    decodage = decodage.push(
        text(format!("Famille : {}", nom_famille))
            .size(13)
            .color(Color::from_rgb8(0xAA, 0xAA, 0xFF)),
    );
    decodage = decodage.push(text(desc_famille).size(11));

    if app.secteurs.len() > 1 {
        for (i, s) in app.secteurs.iter().enumerate() {
            decodage = decodage.push(
                text(format!("Secteur {} — {}  |  T = {:.2}s", i + 1, s.label, s.periode))
                    .size(13)
                    .color(couleur_hex(&s.hex)),
            );
            decodage = decodage.push(
                text(afficher_sequence(&s.sequence, s.famille))
                    .size(11)
                    .font(Font::MONOSPACE),
            );
        }
    } else {
        let s = &app.secteurs[0];
        decodage = decodage.push(
            text(format!("Secteur — {}  |  T = {:.2}s", s.label, s.periode))
                .size(13)
                .color(couleur_hex(&s.hex)),
        );
        decodage = decodage.push(
            text(afficher_sequence(&s.sequence, s.famille))
                .size(11)
                .font(Font::MONOSPACE),
        );
    }

    let hauteur_diagramme = 46.0 * app.secteurs.len() as f32 + 26.0;

    let corps = column![
        scrollable(decodage).height(Length::Fixed(230.0)),
        Canvas::new(Diagramme { secteurs: app.secteurs.clone() })
            .width(Length::Fill)
            .height(Length::Fixed(hauteur_diagramme)),
    ]
    .spacing(6);

    column![barre, info, voyants, corps]
        .spacing(6)
        .padding(8)
        .into()
}

fn main() -> iced::Result {
    iced::application("Visualiseur de phares AISM", update, view)
        .theme(|_: &AppPhare| Theme::Dark)
        .subscription(subscription)
        .window_size(Size::new(820.0, 720.0))
        .run_with(|| (AppPhare::nouveau(), Task::none()))
}

// ---------------------------------------------------------------------------
// Voyant — cercle animé synchronisé sur le temps écoulé depuis depart
// ---------------------------------------------------------------------------

struct VoyantData {
    hex: String,
    label: String,
    sequence: Vec<(bool, f64)>,
    periode: f64,
    depart: Option<Instant>,
}

impl VoyantData {
    fn nouveau(secteur: &Secteur, depart: Option<Instant>) -> Self {
        VoyantData {
            hex: secteur.hex.clone(),
            label: secteur.label.clone(),
            sequence: secteur
                .sequence
                .iter()
                .map(|st| (st.etat == Etat::On, st.duree))
                .collect(),
            periode: secteur.periode,
            depart,
        }
    }

    fn allume(&self, mut t: f64) -> bool {
        t %= self.periode;
        if t < 0.0 {
            t += self.periode;
        }
        for (on, duree) in &self.sequence {
            if t < *duree {
                return *on;
            }
            t -= duree;
        }
        false
    }
}

impl canvas::Program<Message> for VoyantData {
    type State = ();

    fn draw(
        &self,
        _state: &Self::State,
        renderer: &iced::Renderer,
        _theme: &Theme,
        bounds: Rectangle,
        _cursor: iced::mouse::Cursor,
    ) -> Vec<Geometry> {
        let mut frame = Frame::new(renderer, bounds.size());
        let cx = bounds.width / 2.0;
        let cy = bounds.height / 2.0 - 8.0;
        let rayon = (bounds.width / 2.0 - 14.0).max(12.0);

        let couleur_on = couleur_hex(&self.hex);
        let couleur_off = couleur_hex(ETEINT_HEX);

        let allume = self
            .depart
            .map(|d| self.allume(d.elapsed().as_secs_f64()))
            .unwrap_or(false);

        if allume {
            frame.stroke(
                &Path::circle(Point::new(cx, cy), rayon + 5.0),
                Stroke::default()
                    .with_color(couleur_on)
                    .with_width(3.0),
            );
        }

        frame.fill(
            &Path::circle(Point::new(cx, cy), rayon),
            if allume { couleur_on } else { couleur_off },
        );
        frame.stroke(
            &Path::circle(Point::new(cx, cy), rayon),
            Stroke::default()
                .with_color(Color::from_rgb8(0x44, 0x44, 0x44))
                .with_width(2.0),
        );

        frame.fill_text(CanvasText {
            content: self.label.clone(),
            position: Point::new(cx, bounds.height - 14.0),
            color: couleur_on,
            size: Pixels(12.0),
            ..Default::default()
        });

        vec![frame.into_geometry()]
    }
}

// ---------------------------------------------------------------------------
// Diagramme temporel — un axe par secteur sur N_CYCLES de la période max
// ---------------------------------------------------------------------------

struct Diagramme {
    secteurs: Vec<Secteur>,
}

impl canvas::Program<Message> for Diagramme {
    type State = ();

    fn draw(
        &self,
        _state: &Self::State,
        renderer: &iced::Renderer,
        _theme: &Theme,
        bounds: Rectangle,
        _cursor: iced::mouse::Cursor,
    ) -> Vec<Geometry> {
        let mut frame = Frame::new(renderer, bounds.size());
        if self.secteurs.is_empty() {
            return vec![frame.into_geometry()];
        }

        let periode_max = self
            .secteurs
            .iter()
            .map(|s| s.periode)
            .fold(f64::MIN, f64::max);
        let duree_totale = periode_max * N_CYCLES as f64;
        let hauteur_ligne = bounds.height / self.secteurs.len() as f32;

        for (i, secteur) in self.secteurs.iter().enumerate() {
            let top = i as f32 * hauteur_ligne;
            let epaisseur = (hauteur_ligne - 6.0).max(4.0);
            let couleur = couleur_hex(&secteur.hex);

            frame.fill_rectangle(
                Point::new(0.0, top + 2.0),
                Size::new(bounds.width, epaisseur),
                Color::from_rgb8(0x12, 0x12, 0x12),
            );

            let n_cy = ((duree_totale / secteur.periode).round() as usize).max(1);
            let mut t = 0.0;
            for _ in 0..n_cy {
                for st in &secteur.sequence {
                    if st.etat == Etat::On {
                        let x0 = (t / duree_totale) as f32 * bounds.width;
                        let x1 = ((t + st.duree) / duree_totale) as f32 * bounds.width;
                        if x1 > x0 {
                            frame.fill_rectangle(
                                Point::new(x0, top + 2.0),
                                Size::new((x1 - x0).max(1.0), epaisseur),
                                couleur,
                            );
                        }
                    }
                    t += st.duree;
                }
            }

            for k in 1..=n_cy {
                let x = (secteur.periode * k as f64 / duree_totale) as f32 * bounds.width;
                frame.fill_rectangle(
                    Point::new(x, top + 2.0),
                    Size::new(1.0, epaisseur),
                    Color::from_rgb8(0x44, 0x44, 0x44),
                );
            }

            frame.fill_text(CanvasText {
                content: format!("{}  T = {:.1}s", secteur.label, secteur.periode),
                position: Point::new(6.0, top + 6.0),
                color: couleur,
                size: Pixels(11.0),
                ..Default::default()
            });
        }

        vec![frame.into_geometry()]
    }
}

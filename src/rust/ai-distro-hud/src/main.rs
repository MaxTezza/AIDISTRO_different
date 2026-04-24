use eframe::egui;
use futures_util::StreamExt;
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};
use tokio_tungstenite::connect_async;

#[derive(Serialize, Deserialize, Clone, Debug)]
struct AiEvent {
    #[serde(rename = "type")]
    event_type: String,
    message: String,
    title: Option<String>,
    #[serde(default)]
    point: Option<String>,
}

struct HudApp {
    cards: Arc<Mutex<Vec<AiEvent>>>,
}

impl HudApp {
    fn new(_cc: &eframe::CreationContext<'_>, cards: Arc<Mutex<Vec<AiEvent>>>) -> Self {
        Self { cards }
    }
}

impl eframe::App for HudApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        ctx.request_repaint();
    }

    fn ui(&mut self, ui: &mut egui::Ui, _frame: &mut eframe::Frame) {
        let ctx = ui.ctx();
        let mut visuals = egui::Visuals::dark();
        visuals.window_fill = egui::Color32::TRANSPARENT;
        ctx.set_visuals(visuals);

        let cards = self.cards.lock().unwrap();
        let time = ctx.input(|i| i.time);

        // Highlights
        for event in cards.iter().filter(|e| e.event_type == "highlight") {
            if let Some(point_str) = &event.point {
                let parts: Vec<&str> = point_str.split(',').collect();
                if parts.len() == 2 {
                    let x: f32 = parts[0].parse().unwrap_or(0.0);
                    let y: f32 = parts[1].parse().unwrap_or(0.0);
                    let pulse = (time * 5.0).sin() as f32 * 0.5 + 0.5;
                    let radius = 30.0 + (pulse * 10.0);
                    let alpha = (150.0 * (1.0 - pulse)) as u8;
                    let painter = ctx.layer_painter(egui::LayerId::background());
                    painter.circle_stroke(
                        egui::pos2(x, y),
                        radius,
                        egui::Stroke::new(
                            3.0,
                            egui::Color32::from_rgba_unmultiplied(0, 255, 100, alpha),
                        ),
                    );
                    painter.circle_filled(
                        egui::pos2(x, y),
                        5.0,
                        egui::Color32::from_rgb(0, 255, 100),
                    );
                }
            }
        }

        // Info Panel
        egui::Window::new("AI Distro HUD")
            .anchor(egui::Align2::RIGHT_TOP, egui::vec2(-20.0, 20.0))
            .collapsible(false)
            .resizable(false)
            .title_bar(false)
            .frame(
                egui::Frame::window(&ctx.global_style())
                    .fill(egui::Color32::from_black_alpha(180))
                    .inner_margin(10.0),
            )
            .show(ctx, |ui| {
                ui.vertical_centered(|ui| {
                    ui.add(egui::Label::new(
                        egui::RichText::new("COMPUTER")
                            .color(egui::Color32::from_rgb(0, 255, 204))
                            .size(24.0)
                            .strong(),
                    ));
                });
                ui.add_space(5.0);

                // Status Bar
                let last_status = cards.iter().rfind(|e| e.event_type == "status");
                let status_text = last_status
                    .map(|e| e.message.clone())
                    .unwrap_or_else(|| "System Ready".to_string());
                let color = if status_text.contains("Listening") {
                    egui::Color32::from_rgb(255, 0, 85)
                } else {
                    egui::Color32::from_rgb(0, 255, 204)
                };
                ui.group(|ui| {
                    ui.set_width(350.0);
                    ui.label(egui::RichText::new(status_text).color(color).size(16.0));
                });
                ui.add_space(10.0);
                for event in cards
                    .iter()
                    .filter(|e| e.event_type == "info")
                    .rev()
                    .take(3)
                {
                    let is_insight = event.title.as_deref() == Some("proactive_suggestion");
                    let border_color = if is_insight {
                        egui::Color32::from_rgb(255, 204, 0)
                    } else {
                        egui::Color32::from_rgb(0, 255, 204)
                    };
                    egui::Frame::group(ui.style())
                        .stroke(egui::Stroke::new(2.0, border_color))
                        .fill(egui::Color32::from_black_alpha(100))
                        .show(ui, |ui| {
                            ui.set_width(330.0);
                            let title = if is_insight {
                                "Assistant Insight"
                            } else {
                                event.title.as_deref().unwrap_or("Notice")
                            };
                            ui.label(egui::RichText::new(title).strong().color(border_color));
                            ui.separator();
                            ui.label(&event.message);
                        });
                    ui.add_space(10.0);
                }
            });
    }
}

fn main() -> Result<(), eframe::Error> {
    let cards = Arc::new(Mutex::new(Vec::<AiEvent>::new()));
    let cards_clone = Arc::clone(&cards);

    std::thread::spawn(move || {
        let rt = tokio::runtime::Builder::new_multi_thread()
            .enable_all()
            .build()
            .unwrap();
        rt.block_on(async {
            let url = "ws://127.0.0.1:5001";
            if let Ok((mut ws_stream, _)) = connect_async(url).await {
                while let Some(msg) = ws_stream.next().await {
                    let Ok(tokio_tungstenite::tungstenite::Message::Text(text)) = msg else {
                        continue;
                    };
                    let Ok(event) = serde_json::from_str::<AiEvent>(&text) else {
                        continue;
                    };

                    let mut c = cards_clone.lock().unwrap();
                    if event.event_type == "highlight" {
                        c.retain(|e| e.event_type != "highlight");
                    }
                    c.push(event);
                    if c.len() > 30 {
                        c.remove(0);
                    }
                }
            }
        });
    });

    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_transparent(true)
            .with_decorations(false)
            .with_always_on_top()
            .with_maximized(true)
            .with_active(false)
            .with_mouse_passthrough(true),
        ..Default::default()
    };

    eframe::run_native(
        "AI Distro HUD",
        options,
        Box::new(|cc| Ok(Box::new(HudApp::new(cc, cards)))),
    )
}

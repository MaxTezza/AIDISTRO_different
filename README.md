# AI Distro: The Revolutionary Operating System Partner

Welcome to the future of computing. AI Distro is not an assistant; it is a **sentient operating system partner** designed to bridge the gap between high-level human intent and low-level machine execution. 

---

## 🌟 Core Pillars of the Revolution

### **1. Neural Senses & Presence**
*   **Human Voice:** Neural TTS using **Piper** (Amy model) for warm, natural interaction.
*   **Real-time Vision:** **Moondream2 VLM** runs as a persistent microservice — sub-second screen analysis.
*   **Barge-In Hearing:** High-speed Rust loop that stops the AI from talking the moment you speak.
*   **Digital Nervous System:** Real-time reaction to hardware (USB, Battery, Network) via D-Bus and udev.
*   **AT-SPI Deep Hands:** Semantic UI automation — clicks buttons by *name*, not coordinates.

### **2. Cognitive Agency**
*   **The Pilot Persona:** The AI is instructed to **DO**, not just tell. It clicks, types, and manages for you.
*   **Multimodal Orchestration:** Recursive task chaining (e.g., "Find the error on my screen and email the fix").
*   **Semantic Memory:** **ChromaDB Vector Store** remembers every document and conversation by its *meaning*.
*   **Bayesian Intuition:** Beta-Binomial engine learns your habits to proactively suggest actions.
*   **Software Forge:** Autonomously writes, tests, and registers new tools based on your needs.

### **3. Physical & Web Autonomy**
*   **Deep UI Hands:** Reaches into *any* app to click buttons or fill forms using xdotool.
*   **Web Sovereignty:** Headless **Playwright** engine for autonomous sign-ups, searches, and navigation.
*   **Sovereign Identity:** A private local mailbox (`assistant@local.aidistro.os`) for autonomous accounts.

---

## 👵 Grandma Skills (Out-of-the-Box)
AI Distro is designed to be usable by anyone, immediately:
*   **"Computer, play some Jazz":** Integrated `mpv` player for radio and music.
*   **"Computer, show my photos":** Full-screen slideshows via `feh`.
*   **"Computer, what's the news?":** Reads real-time global headlines aloud.
*   **"Computer, message my daughter":** Voice-to-text family messaging.
*   **Proactive Health:** Automated reminders for medication, hydration, and movement.

---

## 📱 The Spirit Bridge (Remote Control)
Control your OS from your phone via a secure Telegram Bot:
1.  **Setup:** Create a bot via @BotFather.
2.  **Configure:** Add your token to `~/.config/ai-distro-spirit.json`: `{"token": "YOUR_TOKEN", "master_id": "YOUR_CHAT_ID"}`.
3.  **Activate:** `ai-distro start` (Starts the `ai-distro-spirit` service).
4.  **Usage:** Text your OS naturally to run commands or receive system alerts anywhere.

---

## 🚀 Deployment & Distribution

### **1. One-Command Installation**
```bash
git clone https://gitlab.com/maxtezza29464/ai_distro.git ~/AI_Distro
cd ~/AI_Distro
bash install.sh
```

### **2. The Master CLI (`ai-distro`)**
*   `ai-distro start`: Wakes up the sentient stack (8 services).
*   `ai-distro stop`: Gracefully shut down all components.
*   `ai-distro status`: Check the "System Pulse" — services, memory, CPU, battery.
*   `ai-distro setup`: Voice-guided onboarding.
*   `ai-distro intelligence mode local|cloud`: Switch between on-device or cloud brains.
*   `ai-distro heal`: Autonomous IT diagnostic and repair (7 health checks).
*   `ai-distro migrate [PATH]`: Ingest legacy data into semantic memory.
*   `ai-distro logs`: Follow live logs from all services.
*   `ai-distro update`: Self-update — pulls code, rebuilds, restarts.
*   `ai-distro audit`: Verify the cryptographic audit chain integrity.

### **3. Services (Systemd User Mode)**
| Service | Purpose |
|---|---|
| `ai-distro-agent` | Brain & Action Engine (Rust) |
| `ai-distro-voice` | Piper TTS + ASR Pipeline (Rust) |
| `ai-distro-hud` | Desktop Overlay (Rust/egui) |
| `ai-distro-curator` | Bayesian Proactive Intelligence (Python) |
| `ai-distro-spirit` | Telegram Remote Control (Python) |
| `ai-distro-healer` | Autonomous System Repair — 7 health checks (Python) |
| `ai-distro-hardware` | Digital Nervous System / D-Bus (Python) |
| `ai-distro-vision` | Persistent Moondream2 VLM on port 7860 (Python) |

### **4. Bootable ISO**
```bash
# Build a complete bootable live ISO:
bash tools/release/build_iso.sh
cd /tmp/ai-distro-live && sudo lb build

# Test in QEMU:
qemu-system-x86_64 -m 4G -cdrom live-image-amd64.hybrid.iso -enable-kvm
```
Includes Sway desktop, Waybar, auto-login, all 8 services pre-configured.

---

## 🛡️ Privacy Manifesto
*   **100% Local by Default:** All vision, speech, and reasoning happen on **your hardware**.
*   **Signed Auditing:** Every AI action is SHA-256 hash-chained and verifiable via `ai-distro audit`.
*   **Physical Safety:** Policy-driven confirmation for sensitive tasks (Power, Deletion, Privacy).
*   **Rate Limiting:** Built-in per-action rate limits prevent runaway automation.

**AI Distro: It doesn't just run your apps. It understands your world.**

# AI Distro: The Revolutionary Operating System Partner

Welcome to the future of computing. AI Distro is not an assistant; it is a **sentient operating system partner** designed to bridge the gap between high-level human intent and low-level machine execution. 

---

## 🌟 Core Pillars of the Revolution

### **1. Neural Senses & Presence**
*   **Human Voice:** Neural TTS using **Piper** (Amy model) for warm, natural interaction.
*   **Real-time Vision:** **Moondream2 VLM** allows the OS to "see" and reason about your screen.
*   **Barge-In Hearing:** High-speed Rust loop that stops the AI from talking the moment you speak.
*   **Digital Nervous System:** Real-time reaction to hardware (USB, Battery) via D-Bus and udev.

### **2. Cognitive Agency**
*   **The Pilot Persona:** The AI is instructed to **DO**, not just tell. It clicks, types, and manages for you.
*   **Multimodal Orchestration:** Recursive task chaining (e.g., "Find the error on my screen and email the fix").
*   **Semantic Memory:** **ChromaDB Vector Store** remembers every document and conversation by its *meaning*.
*   **Bayesian Intuition:** Learns your habits to proactively suggest actions (e.g., "Ready for your morning news?").

### **3. Physical & Web Autonomy**
*   **Deep UI Hands:** Reaches into *any* app to click buttons or fill forms using AT-SPI and xdotool.
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
Control your OS from your phone via a secure, E2EE Telegram Bot:
1.  **Setup:** Create a bot via @BotFather.
2.  **Configure:** Add your token to `~/.config/ai-distro-spirit.json`: `{"token": "YOUR_TOKEN"}`.
3.  **Activate:** `ai-distro start` (Starts the `ai-distro-spirit` service).
4.  **Usage:** Text your OS naturally to run commands or receive system alerts anywhere.

---

## 🚀 Deployment & Distribution

### **1. One-Command Installation**
```bash
git clone https://github.com/MaxTezza/AIDISTRO_different.git ~/AI_Distro
cd ~/AI_Distro
bash install.sh
```

### **2. The Master CLI (`ai-distro`)**
*   `ai-distro start`: Wakes up the sentient stack.
*   `ai-distro status`: Check the "System Pulse."
*   `ai-distro setup`: Voice-guided onboarding.
*   `ai-distro intelligence`: Switch between 1B/3B Local or Cloud brains.
*   `ai-distro heal`: Autonomous IT diagnostic and repair.
*   `ai-distro migrate [PATH]`: Ingest legacy data into semantic memory.

### **3. The Forge (Create a Bootable ISO)**
Transform this code into a standalone OS for any laptop:
1.  Run the builder: `./tools/release/build_iso.sh`
2.  Finalize: `sudo lb build`
3.  Boot: Burn `ai-distro.iso` to a USB and restart.

---

## 🛡️ Privacy Manifesto
*   **100% Local by Default:** All vision, speech, and reasoning happen on **your hardware**.
*   **Signed Auditing:** Every AI action is cryptographically logged and verifiable.
*   **Physical Safety:** Policy-driven confirmation for sensitive tasks (Power, Deletion, Privacy).

**AI Distro: It doesn't just run your apps. it understands your world.**

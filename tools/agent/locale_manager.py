#!/usr/bin/env python3
"""
AI Distro — Multi-Language / Locale Manager

Provides i18n support for persona responses, TTS voice selection,
and UI strings. Ships with English, Spanish, French, German, Portuguese,
and Japanese. Users can add custom locale packs.

Usage:
  python3 locale_manager.py list
  python3 locale_manager.py set es
  python3 locale_manager.py get greeting
  python3 locale_manager.py current
"""
import json
import os
import sys
from pathlib import Path

CONFIG_FILE = Path(os.path.expanduser("~/.config/ai-distro-locale.json"))

# ═══════════════════════════════════════════════════════════════════
# Built-in Locale Packs
# ═══════════════════════════════════════════════════════════════════

LOCALES = {
    "en": {
        "name": "English",
        "tts_voice": "en_US-amy-medium",
        "strings": {
            "greeting": "Hey there! How can I help?",
            "farewell": "See you later!",
            "confirm": "Got it.",
            "error": "Something went wrong. Let me try again.",
            "thinking": "Let me think about that...",
            "listening": "I'm listening...",
            "not_understood": "I didn't quite catch that. Could you say it again?",
            "good_morning": "Good morning! Ready for a great day?",
            "good_evening": "Good evening! Winding down?",
            "battery_low": "Heads up — battery is getting low.",
            "update_available": "There's an update available. Want me to install it?",
            "skill_installed": "New skill installed and ready to go.",
            "wake_word_detected": "I'm here. What do you need?",
            "setup_welcome": "Welcome to AI Distro! Let's get you set up.",
            "setup_complete": "All set! You're ready to go.",
        },
    },
    "es": {
        "name": "Español",
        "tts_voice": "es_ES-mls_10246-low",
        "strings": {
            "greeting": "¡Hola! ¿En qué puedo ayudarte?",
            "farewell": "¡Hasta luego!",
            "confirm": "Entendido.",
            "error": "Algo salió mal. Déjame intentar de nuevo.",
            "thinking": "Déjame pensar en eso...",
            "listening": "Te escucho...",
            "not_understood": "No entendí bien. ¿Puedes repetirlo?",
            "good_morning": "¡Buenos días! ¿Listo para un gran día?",
            "good_evening": "¡Buenas noches! ¿Descansando?",
            "battery_low": "Atención — la batería está baja.",
            "update_available": "Hay una actualización disponible. ¿La instalo?",
            "skill_installed": "Nueva habilidad instalada y lista.",
            "wake_word_detected": "Aquí estoy. ¿Qué necesitas?",
            "setup_welcome": "¡Bienvenido a AI Distro! Vamos a configurarte.",
            "setup_complete": "¡Todo listo! Ya puedes comenzar.",
        },
    },
    "fr": {
        "name": "Français",
        "tts_voice": "fr_FR-upmc-medium",
        "strings": {
            "greeting": "Salut ! Comment puis-je aider ?",
            "farewell": "À bientôt !",
            "confirm": "Compris.",
            "error": "Quelque chose s'est mal passé. Je réessaie.",
            "thinking": "Laissez-moi réfléchir...",
            "listening": "Je vous écoute...",
            "not_understood": "Je n'ai pas bien compris. Pouvez-vous répéter ?",
            "good_morning": "Bonjour ! Prêt pour une belle journée ?",
            "good_evening": "Bonsoir ! On se détend ?",
            "battery_low": "Attention — la batterie est faible.",
            "update_available": "Une mise à jour est disponible. On l'installe ?",
            "skill_installed": "Nouvelle compétence installée et prête.",
            "wake_word_detected": "Je suis là. De quoi avez-vous besoin ?",
            "setup_welcome": "Bienvenue sur AI Distro ! Configurons tout.",
            "setup_complete": "C'est prêt ! Vous pouvez commencer.",
        },
    },
    "de": {
        "name": "Deutsch",
        "tts_voice": "de_DE-thorsten-medium",
        "strings": {
            "greeting": "Hallo! Wie kann ich helfen?",
            "farewell": "Bis bald!",
            "confirm": "Verstanden.",
            "error": "Etwas ist schiefgelaufen. Ich versuche es nochmal.",
            "thinking": "Lass mich darüber nachdenken...",
            "listening": "Ich höre zu...",
            "not_understood": "Das habe ich nicht verstanden. Kannst du das wiederholen?",
            "good_morning": "Guten Morgen! Bereit für einen tollen Tag?",
            "good_evening": "Guten Abend! Entspannst du dich?",
            "battery_low": "Achtung — der Akku ist niedrig.",
            "update_available": "Ein Update ist verfügbar. Soll ich es installieren?",
            "skill_installed": "Neuer Skill installiert und einsatzbereit.",
            "wake_word_detected": "Ich bin da. Was brauchst du?",
            "setup_welcome": "Willkommen bei AI Distro! Lass uns einrichten.",
            "setup_complete": "Alles bereit! Du kannst loslegen.",
        },
    },
    "pt": {
        "name": "Português",
        "tts_voice": "pt_BR-faber-medium",
        "strings": {
            "greeting": "Olá! Como posso ajudar?",
            "farewell": "Até logo!",
            "confirm": "Entendido.",
            "error": "Algo deu errado. Vou tentar de novo.",
            "thinking": "Deixa eu pensar nisso...",
            "listening": "Estou ouvindo...",
            "not_understood": "Não entendi. Pode repetir?",
            "good_morning": "Bom dia! Pronto para um ótimo dia?",
            "good_evening": "Boa noite! Relaxando?",
            "battery_low": "Atenção — bateria baixa.",
            "update_available": "Atualização disponível. Quer instalar?",
            "skill_installed": "Nova habilidade instalada e pronta.",
            "wake_word_detected": "Estou aqui. O que precisa?",
            "setup_welcome": "Bem-vindo ao AI Distro! Vamos configurar.",
            "setup_complete": "Tudo pronto! Pode começar.",
        },
    },
    "ja": {
        "name": "日本語",
        "tts_voice": "ja_JP-kokoro-medium",
        "strings": {
            "greeting": "こんにちは！何かお手伝いしましょうか？",
            "farewell": "またね！",
            "confirm": "了解しました。",
            "error": "問題が発生しました。もう一度試します。",
            "thinking": "考えさせてください...",
            "listening": "聞いています...",
            "not_understood": "よく聞き取れませんでした。もう一度言ってください。",
            "good_morning": "おはようございます！素敵な一日を！",
            "good_evening": "こんばんは！お疲れ様です。",
            "battery_low": "注意 — バッテリーが少なくなっています。",
            "update_available": "アップデートがあります。インストールしますか？",
            "skill_installed": "新しいスキルがインストールされました。",
            "wake_word_detected": "はい、何でしょう？",
            "setup_welcome": "AI Distroへようこそ！セットアップを始めましょう。",
            "setup_complete": "準備完了！始めましょう。",
        },
    },
}


class LocaleManager:
    """Manages locale selection and string retrieval."""

    def __init__(self):
        self.config = self._load_config()
        self.custom_dir = Path(os.path.expanduser("~/.config/ai-distro/locales"))

    def _load_config(self):
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE) as f:
                return json.load(f)
        return {"locale": "en"}

    def _save_config(self):
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=2)

    def get_current(self):
        return self.config.get("locale", "en")

    def set_locale(self, code):
        if code not in LOCALES and not self._has_custom(code):
            return {"error": f"Unknown locale: {code}. Available: {', '.join(self.list_available())}"}
        self.config["locale"] = code
        self._save_config()
        locale_data = self._get_locale_data(code)
        return {"status": "ok", "locale": code, "name": locale_data.get("name", code)}

    def list_available(self):
        codes = list(LOCALES.keys())
        if self.custom_dir.exists():
            for f in self.custom_dir.glob("*.json"):
                codes.append(f.stem)
        return sorted(set(codes))

    def get_string(self, key, fallback=None):
        locale_data = self._get_locale_data(self.get_current())
        return locale_data.get("strings", {}).get(key, fallback or key)

    def get_tts_voice(self):
        locale_data = self._get_locale_data(self.get_current())
        return locale_data.get("tts_voice", "en_US-amy-medium")

    def get_all_strings(self):
        locale_data = self._get_locale_data(self.get_current())
        return locale_data.get("strings", {})

    def _get_locale_data(self, code):
        if code in LOCALES:
            return LOCALES[code]
        custom_file = self.custom_dir / f"{code}.json"
        if custom_file.exists():
            with open(custom_file) as f:
                return json.load(f)
        return LOCALES.get("en", {})

    def _has_custom(self, code):
        return (self.custom_dir / f"{code}.json").exists()


def main():
    mgr = LocaleManager()
    if len(sys.argv) < 2:
        print("Usage: locale_manager.py <list|set|get|current>")
        return

    cmd = sys.argv[1]
    if cmd == "list":
        for code in mgr.list_available():
            data = mgr._get_locale_data(code)
            current = " ← current" if code == mgr.get_current() else ""
            print(f"  {code}  {data.get('name', '?')}{current}")
    elif cmd == "set":
        code = sys.argv[2] if len(sys.argv) > 2 else ""
        print(json.dumps(mgr.set_locale(code), indent=2))
    elif cmd == "get":
        key = sys.argv[2] if len(sys.argv) > 2 else "greeting"
        print(mgr.get_string(key))
    elif cmd == "current":
        print(json.dumps({"locale": mgr.get_current(), "voice": mgr.get_tts_voice()}))
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()

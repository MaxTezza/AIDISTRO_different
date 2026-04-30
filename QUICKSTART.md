# Quick Start

Get AI Distro running in 5 minutes.

## Requirements

- **OS:** Debian 12 / Ubuntu 22.04+ (or boot from the live ISO)
- **RAM:** 4GB minimum, 8GB recommended
- **Disk:** 8GB free (models are ~3GB)
- **CPU:** x86_64 with SSE4.2 (any Intel/AMD from 2012+)

## Option A: Live USB (No Install)

1. Download the ISO from [Releases](https://github.com/MaxTezza/AIDISTRO_different/releases)
2. Flash to USB: `sudo dd if=ai-distro-live.iso of=/dev/sdX bs=4M status=progress && sync`
3. Boot from USB
4. You're in — say **"Hey computer"** or open a terminal

## Option B: Install on Existing Linux

```bash
# 1. Clone
git clone https://gitlab.com/maxtezza29464/ai_distro.git ~/AI_Distro
cd ~/AI_Distro

# 2. Install (downloads models, builds Rust, sets up services)
bash install.sh

# 3. Start
ai-distro start

# 4. Talk
ai-distro ask "What can you do?"
```

## Verify It's Working

```bash
ai-distro doctor    # Check all components
ai-distro status    # See running services
ai-distro logs      # Watch live output
```

## What You Can Do

| Say / Type | What Happens |
|------------|-------------|
| "Hey computer" | Activates voice input |
| "Open Firefox" | Launches Firefox via AT-SPI |
| "What's on my screen?" | Vision model describes your desktop |
| "Play jazz radio" | Starts internet radio stream |
| "Read me the news" | Fetches and reads BBC headlines |
| "Search for Python tutorials" | Opens browser with Google results |
| "Set volume to 50" | Adjusts system volume |
| "How much battery do I have?" | Reports battery status |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "Model not found" | `ai-distro setup` to re-download models |
| No voice output | Check `pulseaudio` is running, try `ai-distro heal` |
| Services won't start | `ai-distro doctor` to diagnose |
| Rust build fails | Ensure `curl`, `gcc`, `pkg-config` are installed |

## Next Steps

- Read the full [README](README.md) for architecture details
- Create custom skills with the [Skill SDK](docs/SKILLS.md)
- Set up [Telegram remote control](docs/PROJECT_BRIEF.md)

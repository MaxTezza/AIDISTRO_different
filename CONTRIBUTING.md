# Contributing to AI Distro

Thanks for wanting to help! Here's how to get involved.

## Getting Started

```bash
git clone https://gitlab.com/maxtezza29464/ai_distro.git ~/AI_Distro
cd ~/AI_Distro
bash install.sh
ai-distro doctor   # Verify everything is working
```

## Development Setup

- **Rust:** `rustup` with stable toolchain. Source is in `src/rust/`
- **Python:** 3.11+, venv in `.venv/`. Tools are in `tools/agent/`
- **Linting:** `cargo clippy`, `cargo fmt`, `ruff check .`

## How to Contribute

### Report a Bug
Open an issue on [GitLab](https://gitlab.com/maxtezza29464/ai_distro/-/issues) with:
- What you expected to happen
- What actually happened
- Output of `ai-distro doctor`
- Your OS and hardware

### Fix a Bug
1. Fork the repo
2. Create a branch: `git checkout -b fix/description`
3. Make your changes
4. Run lints: `cd src/rust && cargo clippy && cargo fmt --check`
5. Run Python lint: `ruff check .`
6. Submit a merge request

### Add a Skill
AI Distro's agent is extensible via Python skills:

1. Create a new file in `src/skills/` or `tools/agent/`
2. Implement a `main()` function that accepts arguments and prints output
3. Register it in `src/skills/dynamic/` with a JSON manifest
4. See `tools/agent/news_reader.py` for a simple example

### Add a Feature
For larger changes, open an issue first to discuss the approach. Areas that need help:
- **ARM64 support** — Raspberry Pi / Apple Silicon
- **Wayland-native** screen capture (currently X11-primary)
- **Additional voice models** and languages
- **Systemd hardening** — sandboxing, resource limits
- **Packaging** — .deb packages, Flatpak, Snap

## Code Style

### Rust
- Run `cargo fmt` before committing
- Zero clippy warnings (`cargo clippy -- -D warnings`)
- Use descriptive error messages, not `.unwrap()`

### Python
- Pass `ruff check .` with no errors
- Use type hints for function signatures
- Docstrings for public functions

## Commit Messages

Use [conventional commits](https://www.conventionalcommits.org/):
```
feat: add bluetooth speaker discovery
fix: handle missing audio device gracefully
docs: update QUICKSTART with ARM instructions
chore: bump sysinfo crate to 0.38
```

## Project Structure

```
AI_Distro/
├── src/rust/          # Rust services (agent, voice, hud, cli)
├── tools/agent/       # Python tool scripts (brain, skills, etc.)
├── src/skills/        # Skill definitions and dynamic skills
├── configs/           # Configuration files
├── iso/               # Live ISO build infrastructure
├── docs/              # Internal documentation
└── install.sh         # One-command installer
```

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).

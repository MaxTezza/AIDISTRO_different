# Installer Plan (ISO)

## Goal
Provide a one‑click install experience via a bootable ISO image.

## Approach
- Build a live ISO with a graphical installer.
- One-click path uses default partitioning and installs AI Distro with KDE + Pop‑like theme + services enabled.

## Components
- `src/infra/iso/` for ISO build assets
- `src/infra/installer/` for installer configs and hooks
- `src/infra/boot/` for bootloader config (GRUB)

## Next Steps
- Choose installer base: Calamares (recommended for GUI) or Subiquity/Ubuntu Desktop.
- Define default partitioning and post‑install hooks.
- Bundle packages: core/voice/agent + KDE + theme + configs.

## Post-install experience
After the Windows-style installer finishes and the user logs in, launch the AI Distro shell as the primary desktop overlay. The first-run experience should:

1. **Welcome screen** — Explain that the assistant serves as the control center, then guide users through choosing a persona and enabling voice replies (Optionally auto-enable voice for those who picked it during install).
2. **Plugin walkthrough** — Highlight the Plugin Catalog help card and describe that every skill is a manifest they can enable/disable with one click; emphasize there are no API keys needed and that safety labels appear on the cards.
3. **Context & memory introduction** — Teach users to use `remember ...` and show the new help card instructions along with the “clear notes / forget tasks” controls (see `docs/CONTEXT.md`). Mention the content is stored locally under `~/.config/ai-distro` and can be reset from the shell settings.
4. **Confirmation finalization** — Reiterate that risky commands always require confirmation, pointing to the policy controls pre-populated in `configs/policy.json`.

Add a “Lite Mode” toggle into that help card so hardware-constrained users can flip the mode during setup; the toggle hits `/api/lite-mode/toggle`, which writes `AI_DISTRO_LIGHTWEIGHT_STATE` and keeps only the core services active until a restart (documented in `docs/RUNTIME_ENV.md`).

Capture these onboarding steps either in the shell onboarding wizard or as a dedicated “Setup complete” card so non-technical people feel guided through configuration without reading API docs. Keep the installer doc updated with any new UX tweaks or installer hooks you add to support this flow.

### Calamares polish checklist
- Add the help-card guidance and Lite Mode toggle to the final shell overlay so users see the instructions immediately after install.
- Ensure the installer writes `/etc/xdg/autostart/ai-distro-shell.desktop` (post-install script now does this) so the assistant begins automatically without user intervention.
- Seed `/etc/skel/.config/ai-distro` with default `providers.json`, `plugins.json`, and `lite-mode.json` so new users inherit sane settings (help card buttons assume those files exist).
- Document these tweaks in release notes and update the Calamares branding assets (`branding.desc`, logos) if you redesign the UI to match the Windows-style setup feel.

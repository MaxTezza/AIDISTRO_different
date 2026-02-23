# MnemonicOS + AI Distro Integration Handoff

## What this repo combines
- **Frontend**: MnemonicOS onboarding shell (steps for name/hostname/timezone, appearance, privacy, persona) now lives in `assets/ui/shell/app.js`, `styles.css`, and the matching `index.html` overlay while keeping the AI Distro branding. Local profile state is stored in `~/.local/state` via the browser (key `ai_distro_user_profile_v1`).
- **Backend**: Pure AI Distro stack (`ai-distro-agent`, `ai-distro-core`, shell backend at `tools/shell/ai_distro_shell.py`) continues to handle IPC, voice commands, runtime actions, and the HTTP APIs that the new frontend consumes.
- **Voice**: Recognition auto-restarts when non-permission errors occur, and helper text explicitly instructs users to hit `Start listening` and speak (wake-word handling is bypassed once onboarding ends).

## Goals for the next person
1. Keep Mnemonic-style onboarding parity while hardening the integration so the UI cannot reopen itself or serve stale assets.
2. Finish the backend workflows (provider connections, starter queue) in sync with the Mnemonic UI cues.
3. Make the overall experience demonstrable: `what can you do`, `open firefox`, `remember ...`, and voice confirmations should work repeatably.

## Current operational checklist
1. Start the services (working directory `/home/jmt3/AI_Distro`):
   ```bash
   AI_DISTRO_IPC_SOCKET=/tmp/ai-distro.sock cargo run --manifest-path src/rust/Cargo.toml --release --bin ai-distro-agent
   AI_DISTRO_CORE_SOCKET=/tmp/ai-core.sock AI_DISTRO_CORE_STATE_DB=/tmp/ai-core-state.db AI_DISTRO_CORE_CONTEXT_DIR=/tmp/ai-core-context cargo run --manifest-path src/rust/Cargo.toml --release --bin ai-distro-core
   AI_DISTRO_IPC_SOCKET=/tmp/ai-distro.sock AI_DISTRO_CORE_SOCKET=/tmp/ai-core.sock AI_DISTRO_SHELL_STATIC_DIR="$PWD/assets/ui/shell" python3 tools/shell/ai_distro_shell.py
   ```
2. Visit `http://127.0.0.1:17842/?reset_onboarding=1`, hard-refresh, and complete each Mnemonic step (enter name + hostname, choose theme/persona/privacy, run sample command). The UI will show `UI build 2026-02-23.5` when fresh assets load.
3. Verify health: `curl -sSf http://127.0.0.1:17842/api/health` should return `core online`; `curl -sSf http://127.0.0.1:17842/api/core/status` reports state details.
4. Confirm voice path: click `Start listening`, speak `what can you do`, then `open firefox`. The helper text will say `Mic interrupted. I will retry automatically.` if the browser fires an intermediate error, and the code will restart the recognizer.

## Key files to inspect
- `assets/ui/shell/app.js`: Mnemonic UX + voice recovery, local profile persistence, onboarding reset logic (`?reset_onboarding=1`), scheduler for automatic restart, and the helper hints tied to `APP_VERSION = 2026-02-23.5`.
- `assets/ui/shell/index.html` & `styles.css`: new onboarding header/exits, form fields, and presentation tweaks needed for the UX.
- `tools/shell/ai_distro_shell.py`: shell backend that now emits `Cache-Control: no-store` so the browser always fetches the latest UI.
- `src/infra/rootfs/live-build/config/includes.chroot/usr/share/ai-distro/ui/*`: mirrored copy of the shell assets for packaging.

## Known issues / TODOs
- Starter setup queue can still halt if confirmation is requested; the UI warns `Waiting for confirmation…` but the queue logic should eventually continue. Rehearse the queue flow (persist updates to `starterInstallQueue`).
- Onboarding is split between local storage flags and backend state—if those get out of sync, use `?reset_onboarding=1` to force a clean start, or remove the `ai_distro_force_disable_onboarding` key via dev tools.
- Voice recognition relies on browser permissions; if the mic dialog is denied, the UI shows “Mic blocked.” The scheduler will retry when the tab regains permission.

## Hand-off tasks
1. Keep the Mnemonic steps: name/hostname/timezone, appearance, persona, privacy/guidance, starter setup (catalog + sample commands). The DOM fragments for each step live under `const onboardingSteps`.
2. Finish the backend connectors (provider connect/test, starter services) so that clicking the sample buttons triggers actual commands without manual restarts.
3. Write tests or automation that run `node --check assets/ui/shell/app.js`, `cargo build`, and `curl http://127.0.0.1:17842/api/health` after launching to ensure all services are responsive.
4. Document any additional dependencies (e.g., voice requires `window.SpeechRecognition`). This file is the next reference for whoever picks up the integration.

## Next actions for whomever inherits this
- Triage pending GitLab pushes if needed (current commit `Restore Mnemonic onboarding and stabilize voice`).
- Validate `app.js` version stamp increments when regenerating assets; the helper text will show the new stamp for quick verification.
- Keep the shell backend’s `Cache-Control` headers so browsers don’t load stale UI snapshots from `src/infra/rootfs/...` during packaging.

# MnemonicOS -> AI_Distro Port Plan

## Current state
- `~/AI_Distro` and `~/Desktop/MnemonicOS` are separate codebases.
- MnemonicOS changes (Tauri UI/native commands) are not present in AI_Distro.
- AI_Distro already has onboarding + persisted state in `assets/ui/shell/app.js` and backend APIs.

## Decision
- AI_Distro is the canonical project moving forward.
- MnemonicOS is treated as a feature branch/prototype source only.

## Port candidates from MnemonicOS
1. Native typed system actions (volume, network, files, weather) with allowlisted execution.
2. No-demo UX policy: remove seeded fake notifications and fake content paths.
3. Persistent identity/state behavior: no reset after restart.
4. Desktop shell polish: widgets, app launcher, quick settings, stable startup flow.

## Immediate execution order
1. Baseline gate:
   - Run `make qa-voice` and capture failing/passing checks.
2. Remove/disable any synthetic/fake data paths in AI_Distro shell APIs.
3. Add explicit provider state to shell UI:
   - Connected/Disconnected for email/calendar/weather providers.
4. Wire real data only in dashboard cards and notifications.
5. Re-run gate and produce proof log.

## Acceptance criteria for this port phase
- No fake seeded notifications.
- No hardcoded demo inbox/calendar/weather entries displayed to user.
- User identity/onboarding survives restart.
- UI shows truthful provider status when not connected.

# AI_Distro Full Handoff (Detailed)

Last updated: 2026-02-23
Owner transfer target: next Codex instance in new terminal

---

## 1) Product Goal (restated)

Primary goal from user:
- Ship a **working product**, not a demo.
- Preserve and restore the UX quality that existed in `Desktop/MnemonicOS`.
- Keep AI_Distro backend/runtime progress, but do not regress setup/onboarding usability.
- Voice interaction is core behavior, not optional.

Non-negotiables from user:
- No fake/demo paths in user-facing behavior.
- Setup must not trap users.
- Users should not need API keys.
- Progress must be visible and concrete.

---

## 2) Why user confidence dropped

Main causes:
1. UX regression vs MnemonicOS baseline:
   - AI_Distro onboarding flow diverged from original MnemonicOS name/personalization flow.
2. Runtime mismatch confusion:
   - stale shell process/port conflicts caused old code paths to be served.
3. Permission failures in shell backend:
   - crashes from `/var/lib/ai-distro-agent` write attempts in user context.
4. Voice behavior instability while onboarding overlay remained active.

This handoff is designed to directly fix those points first.

---

## 3) Current runtime architecture (as of this handoff)

Three-process model (user verified):
- Agent: `ai-distro-agent` over Unix socket `/tmp/ai-distro.sock`.
- Core: `ai-distro-core` over Unix socket `/tmp/ai-core.sock` (with `/tmp` data paths).
- Shell backend: `tools/shell/ai_distro_shell.py` on `127.0.0.1:17842`.

Browser UI:
- `assets/ui/shell/index.html`
- `assets/ui/shell/app.js`
- served by shell backend.

---

## 4) Completed work (exactly what is already done)

### 4.1 Shell backend integration with core (DONE)
File: `tools/shell/ai_distro_shell.py`

Added core socket helper:
- `core_request(payload, timeout=2.0)`

New API routes:
- `GET /api/core/status`
- `GET /api/core/recent-notes?limit=N`
- `POST /api/core/remember-note` with body `{ "note": "..." }`

Health endpoint extended:
- `GET /api/health` now includes `core: {status, message}`

Permission fallback fix (critical):
- Memory and audit path creation no longer hard-fail on `/var/*` permission errors.
- Fallback state path introduced:
  - `~/.local/state/ai-distro-agent/memory`
  - `~/.local/state/ai-distro-agent/audit.jsonl`

Evidence marker strings present:
- `/api/core/status`, `/api/core/recent-notes`, `/api/core/remember-note`

---

### 4.2 Agent confirmation queue (DONE)
File: `src/rust/ai-distro-agent/src/lib.rs`

Before:
- `confirmation_id` placeholder (`temp-id`) and no durable per-request queue logic.

Now:
- Real in-memory bounded queue for pending confirmations:
  - `MAX_PENDING_CONFIRMATIONS = 128`
  - `ConfirmationQueue` with `by_id` map + order deque.
- `RequireConfirmation` stores original request with generated id.
- `confirm` request dequeues id, rechecks policy/rate-limit, executes once.
- Replay with same id returns error.

Tests added and passing:
- `confirm_executes_queued_action_once`
- `confirm_requires_id`

---

### 4.3 Core service de-stubbed (DONE)
File: `src/rust/ai-distro-core/src/main.rs`

Before:
- heartbeat-only loop.

Now:
- Unix socket JSON service with actions:
  - `ping`/`health`
  - `status`
  - `remember_note`
  - `recent_notes`
- Ensures directories/files exist.
- Stores notes in `context_dir/notes.log`.

Added runtime overrides for user/dev execution:
- `AI_DISTRO_CORE_SOCKET`
- `AI_DISTRO_CORE_STATE_DB`
- `AI_DISTRO_CORE_CONTEXT_DIR`

Cargo update:
- `src/rust/ai-distro-core/Cargo.toml` got serde/serde_json deps.

---

### 4.4 Voice service de-stubbed (DONE, baseline)
File: `src/rust/ai-distro-voice/src/main.rs`

Before:
- placeholder stdin flow.

Now:
- Real stdin -> agent socket bridge for `natural_language` requests.
- Optional `speak <text>` mode using configurable TTS command:
  - `AI_DISTRO_TTS_BINARY`
  - `AI_DISTRO_TTS_ARGS`
- Honest structured error on unavailable TTS/socket.

---

### 4.5 UI shell (major updates completed, but with regressions to clean)
File: `assets/ui/shell/app.js` (+ mirrored rootfs copy)

Implemented:
- Voice-first onboarding prompts.
- Hands-free mic toggle and continuous recognition.
- Spoken onboarding controls (`next/back/skip/finish`).
- Spoken confirm/cancel for pending confirmations.
- Core health shown in top status (`Ready · Core online/unavailable`).
- Now-card summary pulls latest core note (`/api/core/recent-notes`).
- `remember ...` command path now posts note to core API directly and early-returns.

Onboarding force-exit controls added:
- `window.aiDistroExitSetup()`
- keyboard combo `Ctrl+Shift+X`
- URL override `?no_onboarding=1`
- completion path closes overlay immediately before async persistence.

Current reality:
- Despite these controls, user still reported being trapped in overlay in live browser session.
- This must be treated as unresolved until proven fixed in-session.

---

### 4.6 Demo-flag cleanup (DONE)
File: `tools/shell/ai-distro-shell-ui.sh`

Removed chromium demo flag:
- `--use-fake-ui-for-media-stream`

---

## 5) Verified checks already run

Build/tests completed in this session:
- `cargo build -p ai-distro-agent -p ai-distro-core -p ai-distro-voice` (pass)
- `cargo test -p ai-distro-agent --lib` (pass)
- `node --check assets/ui/shell/app.js` (pass repeatedly)
- `node --check rootfs mirror app.js` (pass repeatedly)
- `python3 -m py_compile tools/shell/ai_distro_shell.py` (pass)

User-verified API checks:
- `GET /api/health` returned `core: {status: ok, message: core online}`
- `GET /api/core/status` returned `status: ok` and `/tmp` paths

---

## 6) What is still broken (must-fix)

### 6.1 Onboarding overlay trap (OPEN)
Symptoms:
- User still sees onboarding overlay and cannot exit consistently.
- Voice inside wizard also unreliable.

Likely cause now:
- UI state/caching mismatch or stale asset served at least some of the time.
- Possibly completion flags not being read as intended in running JS context.

### 6.2 Voice reliability under live UI session (OPEN)
Symptoms:
- user reports voice works intermittently or only once.

Potential contributors:
- Browser mic permission state transitions.
- recognition error handling and re-entry logic with onboarding state.
- stale JS in active browser tab.

### 6.3 MnemonicOS setup parity (NOT STARTED)
Missing from current flow:
- original name capture + personalization onboarding from MnemonicOS.

---

## 7) Immediate plan for next Codex (strict order)

### Step A (critical): Make onboarding impossible to trap
1. Add explicit visible button in overlay header:
   - `Exit Setup` (not hidden behind keyboard/console).
2. Button handler must:
   - hide overlay immediately,
   - set localStorage completion + force-disable flags,
   - set in-memory `onboardingCompleted=true`,
   - start voice listening if enabled,
   - then async persist via `/api/onboarding`.
3. In `maybeStartOnboarding()`:
   - If either local completion key or force-disable key exists, skip onboarding unconditionally (API state cannot override this).
4. Add a one-time console/info message in app boot indicating onboarding mode and completion source (local vs remote) for diagnostics.

Definition of done:
- User can always leave setup by clicking `Exit Setup`.
- Reload does not reopen wizard unless user explicitly chooses replay.

---

### Step B: Confirm fresh assets are being served
1. Add app version stamp in JS and render it in status/helper text briefly.
2. Verify user sees updated stamp after hard refresh.
3. If not, diagnose cache/process mismatch in shell server static path.

Definition of done:
- User confirms visible version stamp changed after patch.

---

### Step C: Stabilize voice in non-onboarding state
1. Keep wake-word disabled until reliability proven.
2. Show concrete mic-state UX:
   - `Start listening` / `Stop listening`
   - clear error line if mic blocked.
3. Validate command flow in live user session:
   - `what can you do`
   - `open firefox`

Definition of done:
- user gets repeatable voice command execution outside onboarding.

---

### Step D: Restore MnemonicOS onboarding parity
Source to port from:
- `~/Desktop/MnemonicOS/src/shell/OnboardingWizard.tsx`
- related shell files in `~/Desktop/MnemonicOS/src/shell/`

First parity slice:
- bring back name/personalization step and persist it.
- apply user name to shell greeting/title immediately.

Definition of done:
- user sees setup asking for name again and UI reflects it.

---

## 8) Exact commands to run services (user machine)

Terminal 1 (agent):
```bash
cd /home/jmt3/AI_Distro
AI_DISTRO_IPC_SOCKET=/tmp/ai-distro.sock cargo run --manifest-path src/rust/Cargo.toml --release --bin ai-distro-agent
```

Terminal 2 (core):
```bash
cd /home/jmt3/AI_Distro
AI_DISTRO_CORE_SOCKET=/tmp/ai-core.sock AI_DISTRO_CORE_STATE_DB=/tmp/ai-core-state.db AI_DISTRO_CORE_CONTEXT_DIR=/tmp/ai-core-context cargo run --manifest-path src/rust/Cargo.toml --release --bin ai-distro-core
```

Terminal 3 (shell):
```bash
cd /home/jmt3/AI_Distro
AI_DISTRO_IPC_SOCKET=/tmp/ai-distro.sock AI_DISTRO_CORE_SOCKET=/tmp/ai-core.sock AI_DISTRO_SHELL_STATIC_DIR="$PWD/assets/ui/shell" python3 tools/shell/ai_distro_shell.py
```

Health checks:
```bash
curl -sSf http://127.0.0.1:17842/api/health
curl -sSf http://127.0.0.1:17842/api/core/status
```

---

## 9) High-signal file list (most relevant)

- `assets/ui/shell/app.js`
- `assets/ui/shell/index.html`
- `tools/shell/ai_distro_shell.py`
- `src/rust/ai-distro-agent/src/lib.rs`
- `src/rust/ai-distro-core/src/main.rs`
- `src/rust/ai-distro-voice/src/main.rs`
- `tools/shell/ai-distro-shell-ui.sh`
- `src/infra/rootfs/live-build/config/includes.chroot/usr/share/ai-distro/ui/app.js`
- `src/infra/rootfs/live-build/config/includes.chroot/usr/share/ai-distro/ui/index.html`

MnemonicOS source references:
- `~/Desktop/MnemonicOS/src/shell/OnboardingWizard.tsx`
- `~/Desktop/MnemonicOS/src/shell/Shell.tsx`
- `~/Desktop/MnemonicOS/src/shell/DesktopWelcome.tsx`

---

## 10) Known mismatches to clean

- Help text still references wake-word in a few paths; wake-word currently disabled.
- Onboarding logic has multiple force-exit mechanisms; consolidate to single clear path after trap is fixed.
- There are many unrelated modified/untracked repo files from prior work; avoid touching unrelated ones during onboarding/voice stabilization.

---

## 11) Commitment for next pass

Do not add new features until:
1. onboarding trap is gone,
2. voice works consistently outside overlay,
3. user can complete a basic flow without console hacks.

Only then continue broader feature roadmap.


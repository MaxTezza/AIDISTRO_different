# Context Strategy

## Goal
Define how the assistant gathers, stores, and surfaces context so people feel understood without any hidden tracking.

## Current memory flow
- `remember <note>` adds a JSONL entry via `ai-distro-agent` (`src/rust/ai-distro-agent/src/handlers/memory.rs`). Entries live in `AI_DISTRO_MEMORY_DIR` (default `/var/lib/ai-distro-agent/memory/notes.jsonl`) with a timestamp. 
- `read_context` returns the most recent notes (up to 5) so `ai-distro-agent` can summarize what the user explicitly saved.
- The voice/UI layer currently only uses context when the user asks (`remember`, `what do you remember`) and the shell displays a recent-note summary.

## Context categories we expose
1. **Explicit memories:** Notes that a user deliberately saves (`remember the printer is in the office`). These feed the memory file and are surfaced verbatim. The shell should display the latest entry on the dashboard and include it in confirmation prompts when relevant.
2. **Recent tasks:** Actions executed in the last 24h (captured via the audit log). Use the existing audit trail (`AI_DISTRO_AUDIT_LOG`) to show a “Recent activity” card and to help follow-up questions like “What did I ask you to do yesterday?”.
3. **Preferences:** User choices such as volume/brightness targets, provider selections (`~/.config/ai-distro/providers.json`), or `AI_DISTRO_PERSONA` tweaks. This will make the assistant respond with the right tone and UI the next time without re-prompting.
4. **Schedule indicators:** Calendar/weather lookups already exist via the day planner. Surface the upcoming event summary in the shell and allow voice follow-ups (e.g., “Anything on my calendar today?”) to reference cached data instead of calling APIs repeatedly.
5. **Device state:** Minimal system signals (battery, network) tracked by the “nervous system” event stream. Use that to choose polite reminders (“Battery is low, would you like me to dim brightness?”) without storing extra data in memory.

## User experience requirements
- **Transparent control:** Every context write is explicit (remember). `read_context` reuses the same stored notes, and the shell should display the source (“From your saved notes”).
- **Visible context UI:** The shell overlay must show a “Recent context” panel that lists the last 3 notes + last 3 actions. The voice persona can also mention context summaries after confirmation prompts to reassure the user (“I remembered you needed a printer nearby”).
- **Retention policy:** Keep only the last 30 days of audit events for the “Recent tasks” card; older data may be truncated by a nightly job that rotates `AI_DISTRO_AUDIT_LOG` and prunes `notes.jsonl`. Provide an `AI_DISTRO_MEMORY_RETENTION_DAYS` env var to configure this.
- **Easy deletion:** The shell settings must offer “Clear remembered notes” (delete `notes.jsonl`) and “Forget recent tasks” (trim the latest `AI_DISTRO_AUDIT_LOG` entries). Document these actions in `docs/VOICE_UX.md` and `docs/RUNTIME_ENV.md`.
- **Quick reset controls:** The help card exposes buttons that call `/api/context/clear-notes` and `/api/context/forget-tasks`, removing the JSONL memory file and truncating the audit log to `AI_DISTRO_AUDIT_KEEP_LINES` (default 64) so you can reset everything without touching files.
- **Lite mode automation:** Enabling Lite Mode also clears remembered notes and forgets recent tasks automatically, ensuring the assistant starts in a minimal, stateless posture without extra clicks.
- **Tag library:** The shell now summarizes recent notes/tasks into tag-based collections (Photos, Documents, etc.) via `/api/context/tags`. These cards show snippets and suggested voice commands so average users browse by topic rather than file paths.

## Implementation hooks
- The agent already writes the audit log with hash-chaining; expand the shell’s data layer (`ai_distro_shell.py`) to read the latest entries and turn them into cards. The shell may reuse existing IPC actions (e.g., a new `get_context_summary` action) that reads `notes.jsonl` and the audit log.
- The Python brain can conditionally include the last note when building prompts, so the voice response mentions the remembered fact when it fits the intent. Emit a structured `context` field when returning `remember` or `read_context` responses to keep the shell in sync.
- Provide doc guidance for customizing `AI_DISTRO_MEMORY_DIR`, `AI_DISTRO_MEMORY_RETENTION_DAYS`, and `AI_DISTRO_AUDIT_LOG` paths so integrators can store context on encrypted volumes.

## Privacy promise
- No automatic memory writes or remote telemetry tied to personal context. Everything stays local under `~/.config/ai-distro` or `/var/lib/ai-distro-agent`. 
- Audit logs and memory files are hashed and rotated (`AI_DISTRO_AUDIT_ROTATE_BYTES`) to prevent tampering.
- Context features always require explicit confirmation before turning into actions (the existing policy + confirmation system already enforces this). Once the UI adds the “Recent context” card, mention the source so users know what’s being used.

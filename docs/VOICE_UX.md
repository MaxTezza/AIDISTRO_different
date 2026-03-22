# Voice UX (v1)

## Goal
Enable natural English control for system tasks on a KDE-based desktop with Pop-like UX.

## v1 Scope: System Tasks
Focus on safe, high‑value system actions:
- Package install/remove
- System update
- Network toggles (Wi‑Fi/Bluetooth)
- Display/volume/brightness
- Power actions (sleep, reboot, shutdown)
- Open apps and URLs

## Interaction Style
- Natural English with a short confirmation step for risky actions.
- Provide spoken summaries of the action and impact.
- Friendly, conversational tone that feels like a helpful companion.

## Conversational Keep-Alive
For actions that may take a few seconds or minutes, keep the user engaged with short, reassuring filler lines so the experience never feels silent or stalled.
- Use brief, low-friction phrases like “Working on it” or “Almost there.”
- Avoid pretending an action completed if it hasn’t.
- If an action needs confirmation, ask clearly and offer a simple “confirm/cancel” path.

## Companion Persona
The assistant should feel like a helpful friend that gets to know the user over time.
- Warm and approachable, but not overly casual.
- Remembers user-provided facts when explicitly asked to “remember.”
- Offers short check-ins during longer tasks without being distracting.

## Examples
- "Install Firefox" -> `package_install` payload: `firefox`
- "Update the system" -> `system_update` payload: `stable`
- "Turn on Wi‑Fi" -> `network_wifi_on`
- "Set volume to 40%" -> `set_volume` payload: `40`
- "Restart the computer" -> `power_reboot` (confirm)
- "Check my Gmail" -> `open_url` payload: `https://mail.google.com/`
- "Open Firefox" -> `open_app` payload: `firefox`

## Confirmation Rules
- Required for:
  - package installs
  - system updates
  - power actions
- Denied by policy for destructive commands (see `policy.json`).

## Error Handling
- If intent cannot be mapped, respond with a clarification prompt.
- If policy denies action, explain the reason.

## Context Awareness
-  Use `remember <text>` to capture explicit facts; they are stored via `ai-distro-agent` and surfaced whenever the user asks “what do you remember.”
-  Provide a “Recent context” panel in the shell that shows the last saved notes plus a short list of recent actions derived from `AI_DISTRO_AUDIT_LOG`. Mention the source every time the assistant references stored information, keeping transparency high.
-  Limit context to the most recent 5 notes and 30 days of audit entries; point the voice persona to the new `docs/CONTEXT.md` for details so people understand what is kept and how to clear it.
-  When an action reuses remembered context (e.g., a follow-up about the printer), remind the user (“You asked me to remember the printer, should I use that location?”) before proceeding.
-  The help card includes buttons to clear notes or forget tasks without visiting the filesystem; use them to reset context before restarting the assistant.
-  The help card also exposes a Lite Mode toggle that hits `/api/lite-mode/toggle` so users on older hardware can throttle background services without editing configuration files.
-  The new Tag Library reads your recent notes and tasks for hints like “photos,” “documents,” or “downloads,” and presents them as collections you can explore by voice or click (say “show my photos” or tap the button). This keeps file browsing tag-based instead of path-based.

## Plain-language error messaging
-  When the agent returns an error or the IPC layer disconnects, the shell rewrites the response into human-friendly instructions (e.g., “Network hiccup detected” instead of a stack trace). This keeps the interface calm and prevents panic when something goes wrong.

## Future Enhancements
- App navigation
- File actions
- Context-aware personalization

# Runtime Environment Variables

## Agent
- `AI_DISTRO_IPC_SOCKET` (default: `/run/ai-distro/agent.sock`)
  Path to Unix socket for IPC.

- `AI_DISTRO_IPC_SOCKET_MODE` (default: `660`)
  Octal permission mode applied to the IPC socket (for example: `660`, `600`).

- `AI_DISTRO_IPC_STDIN` (default: unset)
  If set to `1`, run the IPC loop over stdin/stdout.

- `AI_DISTRO_INTENT_PARSER` (default: `/usr/lib/ai-distro/intent_parser.py`)
  Path to the intent parser CLI for natural language requests.

- `AI_DISTRO_DAY_PLANNER` (default: `/usr/lib/ai-distro/day_planner.py`)
  Helper script for weather + calendar clothing recommendations (`plan_day_outfit`).

- `AI_DISTRO_WEATHER_TOOL` (default: `/usr/lib/ai-distro/weather_router.py`)
  Helper script for direct forecast requests (`weather_get`), using live no-key weather first and local fallback when needed.

- `AI_DISTRO_CALENDAR_TOOL` (default: `/usr/lib/ai-distro/calendar_tool.py`)
  Helper script for local calendar add/list requests (`calendar_add_event`, `calendar_list_day`).

- `AI_DISTRO_CALENDAR_ROUTER` (default: `/usr/lib/ai-distro/calendar_router.py`)
  Provider router for calendar actions (`local`, `google`, `microsoft`).

- `AI_DISTRO_GMAIL_TOOL` (default: `/usr/lib/ai-distro/gmail_tool.py`)
  Helper script for Gmail actions (`email_inbox_summary`, `email_search`, `email_draft`).

- `AI_DISTRO_EMAIL_ROUTER` (default: `/usr/lib/ai-distro/email_router.py`)
  Provider router for email actions (`gmail`, later `outlook`).

- `AI_DISTRO_PROVIDERS_FILE` (default: `~/.config/ai-distro/providers.json`)
  Provider selection file used by routers and shell UI.

- `AI_DISTRO_CALENDAR_PROVIDER`, `AI_DISTRO_EMAIL_PROVIDER`, `AI_DISTRO_WEATHER_PROVIDER`
  Optional provider overrides for routing without editing provider config files.

- `AI_DISTRO_GOOGLE_CALENDAR_OAUTH_FILE` (default: `~/.config/ai-distro/google-calendar-oauth.json`)
  OAuth config for Google Calendar integration (`client_id`, `client_secret`, `refresh_token`, `calendar_id`).

- `AI_DISTRO_GOOGLE_GMAIL_OAUTH_FILE` (default: `~/.config/ai-distro/google-gmail-oauth.json`)
  OAuth config for Gmail integration (`client_id`, `client_secret`, `refresh_token`).

- `AI_DISTRO_MICROSOFT_OUTLOOK_OAUTH_FILE` (default: `~/.config/ai-distro/microsoft-outlook-oauth.json`)
  OAuth config for Outlook integration (`client_id`, `client_secret`, `tenant_id`, `refresh_token`).

- `AI_DISTRO_GOOGLE_CLIENT_ID`, `AI_DISTRO_GOOGLE_CLIENT_SECRET`, `AI_DISTRO_GOOGLE_REFRESH_TOKEN`
  Optional env overrides for Google Calendar OAuth credentials.

- `AI_DISTRO_GOOGLE_GMAIL_REFRESH_TOKEN`
  Optional env override for Gmail refresh token (or reuse `AI_DISTRO_GOOGLE_REFRESH_TOKEN`).

- `AI_DISTRO_MICROSOFT_CLIENT_ID`, `AI_DISTRO_MICROSOFT_CLIENT_SECRET`, `AI_DISTRO_MICROSOFT_REFRESH_TOKEN`
  Optional env overrides for Outlook integration.

- `AI_DISTRO_MICROSOFT_TENANT_ID` (default: `common`)
  Microsoft Entra tenant for OAuth token exchange.

- `AI_DISTRO_MICROSOFT_OUTLOOK_SCOPE`
  OAuth scopes for Outlook integration (default: `Mail.Read` for read actions, `Mail.ReadWrite` for draft actions).

- `AI_DISTRO_MICROSOFT_CALENDAR_SCOPE`
  OAuth scopes for Microsoft Calendar integration (default: `Calendars.Read` for list and `Calendars.ReadWrite` for add).

- `AI_DISTRO_IMAP_HOST`, `AI_DISTRO_IMAP_PORT` (default: `993`)
  IMAP server host/port for generic email provider mode.

- `AI_DISTRO_IMAP_USERNAME`, `AI_DISTRO_IMAP_PASSWORD`
  IMAP credentials (for many providers or Proton Bridge local credentials).

- `AI_DISTRO_IMAP_FOLDER` (default: `INBOX`)
  Mail folder used for summary/search in IMAP mode.

- `AI_DISTRO_IMAP_TLS_MODE` (default: `ssl`)
  IMAP transport mode: `ssl` (IMAP4_SSL) or `starttls` (IMAP + STARTTLS).

- `AI_DISTRO_GOOGLE_CALENDAR_ID` (default: `primary`)
  Calendar ID used for Google Calendar event fetch.

- `AI_DISTRO_INTENT_STDIN` (default: unset)
  If set to `1`, read natural language text from stdin and emit intent JSON.

## Confirmations
- `AI_DISTRO_CONFIRM_DIR` (default: `/var/lib/ai-distro-agent/confirmations`)
  Directory to persist pending confirmation records.

- `AI_DISTRO_CONFIRM_TTL_SECS` (default: `300`)
  Confirmation expiration time in seconds.

- `AI_DISTRO_CONFIRM_CLEANUP_SECS` (default: `300`)
  Cleanup interval in seconds.

## Shell
- `AI_DISTRO_SHELL_HOST` (default: `127.0.0.1`)
  Shell server bind address.

- `AI_DISTRO_SHELL_PORT` (default: `17842`)
  Shell server port.

- `AI_DISTRO_SHELL_STATIC_DIR` (default: `/usr/share/ai-distro/ui/shell`)
  Path to shell UI assets.

- `AI_DISTRO_PERSONA` (default: `/etc/ai-distro/persona.json`)
  Path to assistant persona configuration.

- `AI_DISTRO_AUDIT_LOG` (default: `/var/log/ai-distro-agent/audit.jsonl`)
  JSONL audit trail destination for action outcomes (request metadata, decision/result status).

- `AI_DISTRO_AUDIT_STATE` (default: `${AI_DISTRO_AUDIT_LOG}.state`)
  Path for persisted hash-chain state (`seq`, `last_hash`) used to verify continuity across restarts.

- `AI_DISTRO_AUDIT_ROTATE_BYTES` (default: `5242880`)
  Rotate audit log when it reaches this size (bytes); a hash-chained rotation anchor is written into the new file.

- `AI_DISTRO_WEATHER_LOCATION` (default: `Austin`)
  Location passed to the day planner weather fetch.

- `AI_DISTRO_CALENDAR_EVENTS_FILE` (default: `~/.config/ai-distro/calendar-events.json`)
  Local calendar events source used by the day planner.

## Lightweight mode helpers
- `AI_DISTRO_LIGHTWEIGHT_MODE` (default: unset)
  Set to `1` to keep only the minimal services running (agent, shell, basic brain) and skip optional routers. This mode disables background proactive polls and limits audit writes to the latest 100 lines so the distro stays lean on older hardware.
- `AI_DISTRO_LIGHTWEIGHT_SKILLS` (default: `core`)
  Comma-separated list of skill directories to load in lightweight mode; use `core` for the built-in manifests or point to smaller subsets you trust.
- `AI_DISTRO_LLM_CACHE_TTL_SECS` (default: `300`)
  Reduce model reload frequency by caching responses in-memory; useful when running on limited RAM. Set to `0` to disable caching completely.

*When the shell help card toggles Lite Mode, it also clears remembered notes and trims the audit log automatically, so the assistant starts fresh in the minimal profile; `AI_DISTRO_LIGHTWEIGHT_STATE` records the current toggle state (`/api/lite-mode`).*

*Use these env vars in tandem with the install doc's “lite” switch so the shell can expose a toggle that launches the assistant without extra services, then lets users add plugins once they’re comfortable.*

- `AI_DISTRO_LIGHTWEIGHT_STATE` (default: `~/.config/ai-distro/lite-mode.json`)
  File used by the shell help card to persist the Lite mode toggle; the shell exposes `/api/lite-mode` (GET) and `/api/lite-mode/toggle` (POST) so you can switch modes without editing environment configuration manually.

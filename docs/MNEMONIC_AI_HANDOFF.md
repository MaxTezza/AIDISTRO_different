# MnemonicOS + AI Distro Integration (Unified)

## Status: Unified System
The "back and forth" between the prototype and the runtime has been resolved. AI Distro and Mnemonic OS are now **one thing**.

- **Frontend**: The Mnemonic OS shell is the official interface, living in `assets/ui/shell/`. 
  - Integrated Command Bar (`Cmd+Space`) for app launching.
  - Persistent system widgets (CPU, MEM, Clock) powered by `/api/system/stats`.
- **Backend**: Unified Python/Rust stack in `AI_Distro` handles all logic. The prototype React/Tauri code has been archived to `legacy/mnemonicos_prototype`.
- **Truthful UI**: Hardcoded demo data and "fake" notifications have been removed in favor of real audit-log alerts and provider status.

## Operational Checklist
1. **Start Services** (Unified Command):
   ```bash
   AI_DISTRO_IPC_SOCKET=/tmp/ai-distro.sock cargo run --manifest-path src/rust/Cargo.toml --release --bin ai-distro-agent
   AI_DISTRO_CORE_SOCKET=/tmp/ai-core.sock AI_DISTRO_CORE_STATE_DB=/tmp/ai-core-state.db AI_DISTRO_CORE_CONTEXT_DIR=/tmp/ai-core-context cargo run --manifest-path src/rust/Cargo.toml --release --bin ai-distro-core
   AI_DISTRO_IPC_SOCKET=/tmp/ai-distro.sock AI_DISTRO_CORE_SOCKET=/tmp/ai-core.sock AI_DISTRO_SHELL_STATIC_DIR="$PWD/assets/ui/shell" python3 tools/shell/ai_distro_shell.py
   ```
2. **Access UI**: `http://127.0.0.1:17842/`
3. **Verify Unification**:
   - Press `Cmd+Space` (or `Ctrl+Space`) to open the Mnemonic Command Bar.
   - Observe real-time system stats in the top header.
   - Check the "Notifications" panel for real system events.

## Key Files (Single Source of Truth)
- `assets/ui/shell/app.js`: Main shell logic, including launcher and widgets.
- `tools/shell/ai_distro_shell.py`: Backend serving `/api/apps` and `/api/system/stats`.
- `legacy/mnemonicos_prototype/`: **ARCHIVED** - reference only. Do not edit.

## Next Steps for Maintenance
- **Launcher**: Improve the fuzzy search logic in `app.js` for better app discovery.
- **Widgets**: Add more metrics (e.g., Disk, Network) to the `/api/system/stats` endpoint.
- **Safety**: Continue hardening the confirmation gates for all system-level actions.

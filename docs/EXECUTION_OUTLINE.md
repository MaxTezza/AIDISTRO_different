# AI_Distro Execution Outline (from `Desktop/everything`)

Goal: fully operational distro for non-technical users, developers, and power users; no demo behavior.

## Phase 0: Stabilize the current shell (small steps)
1. Remove manual API-key/OAuth code-paste UI from provider setup. `Done`
2. Add provider truth states (Connected / Needs setup / Error) in sidebar cards. `Done`
3. Remove synthetic notifications; show only real system/provider events. `Done`
4. Add plain-language error mapping for top failure classes. `Done`

## Phase 1: Real user data layer
1. Universal search v1 across files/settings/apps/provider metadata. `Done`
2. Calendar live provider read + local fallback with explicit status labels. `Done`
3. Email live provider read + local fallback with explicit status labels. `Done`
4. Weather provider normalization with no-key default and testable fallback. `Done`

## Phase 2: OS behavior essentials
1. Snap window management + workspace persistence. `Pending`
2. Dark/light schedule + focus mode granularity. `Pending`
3. Trusted app catalog UX with safe install flow defaults. `Pending`
4. Human-readable diagnostics and one-click remediation hooks. `Pending`

## Phase 3: Distro substrate
1. Atomic update + rollback path (Btrfs snapshot flow). `Pending`
2. Recovery/restore UX in boot and shell. `Pending`
3. Driver/device readiness pipeline. `Pending`
4. Packaging + installer hardening for repeatable release builds. `Pending`

## Working rules
- Each step must be independently testable.
- No step should combine unrelated concerns.
- No fake data in user-facing UI.
- If a feature is incomplete, show truthful status in UI.

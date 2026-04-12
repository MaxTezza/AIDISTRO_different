# MnemonicOS Feature Roadmap (from Desktop `everything` docs)

## Product rules
- No hardcoded demo user data in core experiences.
- No requirement for end users to enter API keys.
- Sign-in should look like regular consumer OAuth/web login flows.
- Advanced system controls must remain hidden behind plain-language UX.

## Phase A: App-to-OS bridge (in progress)
- [x] Replace unrestricted native shell endpoint with typed native tools.
- [x] Real filesystem-backed Files app (no mock file list).
- [x] Weather via zero-key provider (`wttr.in`) with fallback cache.
- [x] Real network/privacy widgets via dedicated native commands.
- [x] Email app default state switched from fake inbox to connect/open-provider flow.
- [ ] Calendar provider integration (local calendar + optional cloud bridge).
- [ ] Replace remaining mock notifications/content seeds.

## Phase B: No-demo productivity stack
- [ ] OAuth account linking panel (Google/Microsoft) with secure token storage.
- [ ] Real inbox sync (IMAP/OAuth or provider APIs with app-managed credentials).
- [ ] Real calendar sync and event CRUD.
- [ ] Unified search across files/settings/email/calendar.

## Phase C: OS/Distro migration
- [ ] Atomic update + rollback substrate (Btrfs snapshots).
- [ ] Curated app-store-first package model.
- [ ] Driver and hardware auto-setup pipeline.
- [ ] Snapshot restore UX ("restore to yesterday").
- [ ] Live USB and installer path.

## Notes
- GitHub is no longer target remote. Prepare repo for GitLab remote + CI only.

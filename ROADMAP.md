# AI Distro Roadmap

## Phase 1 – Lightweight Core & Context (now)
- Keep the Rust/Brain/Shell stack lean and configurable (`docs/RUNTIME_ENV.md`).
- Finalize the context strategy (see `docs/CONTEXT.md`) so “remember/read context” is transparent.
- Deliver the plugin manifest spec (`docs/PLUGIN_MANIFEST.md`) and register the core skill directory (`docs/SKILLS.md`).
- Harden the local LLM workflow so the assistant can operate without paid APIs, and keep the shell responsive on average hardware.

## Phase 2 – Everyday User Plugins (next)
- Expand the manifest catalog with curated plugins (weather, calendar, power, package install) that expose their metadata to both voice and shell.
- Build the shell plugin catalog UI to read `category`, `tags`, and `safety` info from each manifest and surface confirmations.
- Document how third parties can create new manifests, use `AI_DISTRO_SKILLS_DIR`, and extend the plugin policy via `configs/policy.json`.

## Phase 3 – Developer/Power Plugins
- Define plugin dependencies and routing so dev-focused skills (build/test, container launch, remote tools) can reuse the manifest schema.
- Add an IPC action for `get_context_summary` coupled to the manifest metadata so conversations can reference stored notes + audit events (per `docs/CONTEXT.md`).
- Enable plugin lifecycle commands (install, enable, disable) in the shell and link them to the manifest safety/confirmation rules.

## Phase 4 – Release polish
- Create a “plugin marketplace” style entry in the shell that lists available manifest-based skills by category and allows one-click activation.
- Keep running `make qa-voice`/`cargo test` in CI, include plugin manifest coverage in automated suites, and regenerate docs whenever the manifest spec evolves.
- Produce a final “common user checklist” describing how to configure context, plugins, and lightweight LLM options.

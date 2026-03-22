## Skill & Plugin Directory

AI Distro reads every JSON skill manifest under `src/skills/core` (or the path in `AI_DISTRO_SKILLS_DIR`). Those manifests follow the format described in [`docs/PLUGIN_MANIFEST.md`](PLUGIN_MANIFEST.md) and are loaded both by the Python brain (`tools/agent/brain.py`) and the Rust agent (`ai_distro_agent::load_skills`).

Add new plugin manifests by dropping a JSON file into that directory, keeping the `name`, handler, parameters, examples, and safety metadata aligned with the manifest spec so the assistant can safely expose it to both voice and shell users.

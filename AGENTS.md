# Repository Agent Instructions

## GitHub-first SDLC
- Source of truth: this repository. Work in a feature branch; never edit the installed Plugin directly for ordinary feature changes.
- Prefer one atomic commit per feature or coherent fix. Stage related files together; do not commit per file. Run local validation before pushing, then open a PR; merge only after green CI. Do not force-push without explicit approval.
- Keep shared/ generic and platforms/gpt + platforms/grok compatible. Put named real-world regression examples in tests/cases/, never in runtime references.

## Mandatory pre-push checks
1. Read scripts/skill_sources.py and platforms/{gpt,grok}/overrides.json when changing shared or platform files.
2. The assembler merges shared/<skill>/, platforms/<platform>/_common/, then platforms/<platform>/<skill>/. Any path present in both shared and a platform is a collision **even when contents match**.
3. A collision is valid only when explicitly declared for that skill in platforms/<platform>/overrides.json. Avoid redundant platform duplicates: prefer deleting the platform file when the shared rule is sufficient. Only declare overrides for genuinely platform-specific differences.
4. Run: python scripts/validate-skills.py; python -m unittest discover -s tests -v; python scripts/build-skills.py --help (then run the documented build invocation); verify both platform archives and links. If a command cannot run, say so and do not claim local tests passed.
5. On CI failure, read the failing job log and trace the exact check in scripts, not just the error string. Fix the root cause in one cohesive commit, then wait for the new run and inspect its actual result before saying it is resolved.
6. Preserve frontmatter as the first bytes of SKILL.md, with only name and description, matching directory name. Verify relative links and metadata.
7. Do not weaken validators or inflate expected skill counts to conceal source errors.
8. Merge-triggered sync must verify installed skill inventory and source SHA; deployment is not complete merely because a job triggered.

## Safety and authorization
Do not modify unrelated Skills, publish to Grok, merge PRs, or delete installed assets unless specifically authorized. Preserve private user data and existing release assets. Repository instructions do not override higher-priority platform policies.

# Architecture V2 Skill rename / migration plan (proposal)
Status: NOT EXECUTED. Existing installations remain unchanged.
Proposed new skill id: art-culture-expert-guide
Replaces: travel-architecture-deep-guide
Scope: world architecture, fine art, archaeology, religious art, cultural history, museum objects, urban heritage and field interpretation.

## Source changes required before merge
1. Move shared/travel-architecture-deep-guide -> shared/art-culture-expert-guide.
2. Move platforms/gpt/travel-architecture-deep-guide -> platforms/gpt/art-culture-expert-guide.
3. Move platforms/grok/travel-architecture-deep-guide -> platforms/grok/art-culture-expert-guide.
4. Change frontmatter name and agents metadata; update README, build/test references, expected skill inventories and any downstream mentions.
5. Preserve historical migration mapping in repository documentation, not as runtime dependency.
6. Validate both platform builds, archive content, skill discovery and regression tests.

## Deployment sequence after approved PR merge
- Build and validate both new packages from exact merged commit.
- Install new skill on GPT and Grok without deleting old.
- Verify new skill discoverable and field-guide tests work.
- Remove old skill on each platform only after new install verification and explicit authorized deployment.
- Check inventory for duplicate and missing skills, record source commit and release status.
- On failure, retain old skill and report; never silently delete.
No rename/delete/deployment is performed by this planning document.
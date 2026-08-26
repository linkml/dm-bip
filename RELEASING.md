# Release Process

## Choosing a Version Number

A version protects a *contract*. Each number answers "what happens if someone pulls this?"

dm-bip's contract is not a code API — nobody imports it. It is two things:

1. **Operating interface** — how you invoke and deploy: Make targets, `DM_*` config variables, CLI verbs, container inputs. Operators depend on this.
2. **Output** — the shape of the harmonized data and its BDCHM conformance. Downstream data consumers depend on this.

Work through these in order:

| | Test | Result |
|---|---|---|
| 1 | Must an operator change how they invoke or deploy, or a consumer change how they read output? | **Major** — bump 1st, zero the rest |
| 2 | Else, is there anything new they *can* use? | **Minor** — bump 2nd, zero the 3rd |
| 3 | Else — fixes, safer dependencies, performance, docs? | **Patch** — bump 3rd |

A bug fix that *changes* output for the broken cases is still a patch: the contract was always "be correct," and the code just met it. Only escalate if you are changing what correct means.

**Tempo.** Patches are low-ceremony and frequent, with no RC cycle — adopting one should be a no-brainer. Minors are batched and deliberate, and earn an RC cycle because there is new behavior worth exercising. Majors are rare, announced, and always get an RC.

Cut patches eagerly. The anti-pattern is letting fixes and behavior-neutral dependency bumps pile up until they ride into the next minor, which wastes the third number's signal.

## GitHub Releases

1. Create release candidate tags (`v<X.Y.Z>-rc<N>`) for testing.
2. When ready, create a GitHub release with tag `v<X.Y.Z>`.

Documentation is deployed separately on pushes to `main`.

## BDC Container Deployment

Container images are pushed to the Seven Bridges Image Registry via GitHub Actions. Three deployment tiers are available:

| Trigger | Registry Target | `BDC_PULL_LATEST` | Purpose |
|---------|----------------|-------------------|---------|
| Push to `docker-dev` | `SB_REGISTRY_PROJECT_DEV` | `true` | Dev: mutable, pulls latest dependency branches |
| Push to `docker-push-7bridges` | `SB_REGISTRY_PROJECT` | `false` | Test: pinned dependency tags, for validation |
| Push `bdc-v*` tag | `SB_REGISTRY_PROJECT_PROD` | `false` | Prod: pinned dependency tags, release deployments |

### Dev (`docker-dev` branch)

For testing pipeline changes (new code, updated dependencies). Images are built with `BDC_PULL_LATEST=true`, so external repos (trans-specs, harmonized variables) are cloned at their default branch and can be updated with `git pull` at runtime.

### Test (`docker-push-7bridges` branch)

For testing data work through a known-good pipeline (new trans-specs, speculative transformations, QA/QC). Images are built with pinned dependency tags. Push commits to this branch to trigger a build to the test registry.

### Prod (`bdc-v*` tags)

For release deployments. Tag format: `bdc-v<X.Y.Z>`. Images are built with pinned dependency tags and pushed to the production registry.

```bash
# Example: deploy v1.2.0 to prod
git tag bdc-v1.2.0
git push origin bdc-v1.2.0
```

## Required GitHub Configuration

### Variables (Settings > Secrets and variables > Actions > Variables)

- `SB_REGISTRY` -- Seven Bridges registry hostname
- `SB_REGISTRY_USERNAME` -- Registry account username
- `SB_REGISTRY_PROJECT_DEV` -- Dev registry path segment
- `SB_REGISTRY_PROJECT` -- Test registry path segment
- `SB_REGISTRY_PROJECT_PROD` -- Prod registry path segment

### Secrets

- `SB_REGISTRY_PASSWORD` -- Registry auth token

## Seven Bridges App Setup

Each deployment tier has a corresponding app on the Seven Bridges platform, whose Docker Repository field points at a registry path:

```
<SB_REGISTRY>/<SB_REGISTRY_USERNAME>/<REGISTRY_PROJECT>/dm-bip-env:<TAG>
```

| App | Pulls | Moves when |
|-----|-------|------------|
| `cc-dm-bip-test` (dev) | `dm-bip-docker-dev/dm-bip-env:latest` | every push to `docker-dev` |
| `bdc-dm-bip-prod` (prod) | `dm-bip-prod/dm-bip-env:prod` | a non-rc `bdc-v*` tag is pushed |

**Prod deploys by moving a tag, not by editing the app.** The `:prod` tag is a promotion pointer: pushing `bdc-v<X.Y.Z>` builds the image, tags it both `bdc-v<X.Y.Z>` and `prod`, and the app picks it up on its next run. Pre-release tags containing `-rc` are excluded from `:prod`, so a release candidate can never become production.

This means the app definition does not record which version prod is running. That is recoverable: every run writes `version`, `git_ref`, and `build_date` into its provenance output. To roll back, re-push `:prod` pointing at the older image rather than editing the app.

Referencing an app without a trailing revision number resolves to its latest revision, so app revisions can change without breaking clients. `dm-bip seven-bridges submit --app <id>/<N>` still pins an explicit revision when you need one for testing.

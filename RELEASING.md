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

| Trigger | Registry Target Variable | SBG Image Repository | `BDC_PULL_LATEST` | Purpose |
|---------|-------------------------|----------------------|-------------------|---------|
| Push to `docker-dev` | `SB_REGISTRY_PROJECT_DEV` | `dm-bip-docker-dev` | `true` | Dev: mutable, pulls latest dependency branches |
| Push to `docker-push-7bridges` | `SB_REGISTRY_PROJECT_DEVELOP` | `dm-bip-develop` | `false` | Test: pinned dependency tags, for validation |
| Push `bdc-v*` tag | `SB_REGISTRY_PROJECT_PROD` | `dm-bip-prod` | `false` | Prod: pinned dependency tags, release deployments |

This mapping is implemented in exactly one place: the `Configure build for branch`
step of `.github/workflows/docker-push-7bridges-dev.yml`. There is no other
branch-to-repository logic anywhere in the repo. To retarget a tier, change the
variable value in GitHub -- not the workflow.

Each tier owns one repository, so no two triggers overwrite the same `:latest`.
Note that a branch does not select a repository -- a *tier* does. Any push that
is not `docker-dev` and not a `bdc-v*` tag (including a manual
`workflow_dispatch` from an arbitrary branch) builds as the test tier.

Until 2026-08-26 the dev and test tiers shared `dm-bip-docker-dev`, so `:latest`
there was last-writer-wins between the `docker-dev` and `docker-push-7bridges`
branches. If an SBG app still points at `dm-bip-docker-dev` for test-tier work,
repoint it to `dm-bip-develop`.

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

All five are **required**. Deleting any one of them breaks the tier that uses
it: GitHub substitutes an empty string for an undefined `vars.*` reference, so
the workflow fails in `Configure build for branch` naming the missing variable.

- `SB_REGISTRY` -- Seven Bridges registry hostname (host only, no scheme, no `/v2`)
- `SB_REGISTRY_USERNAME` -- Registry account username; also used as the image
  namespace segment. On a division-scoped BDC account this is the qualified form
  (for example `<user>-<division>`).
- `SB_REGISTRY_PROJECT_DEV` -- Dev registry path segment
- `SB_REGISTRY_PROJECT_DEVELOP` -- Test registry path segment
- `SB_REGISTRY_PROJECT_PROD` -- Prod registry path segment

Do not prune a `SB_REGISTRY_PROJECT_*` variable on the assumption that an unused
*name* means an unused *tier*. `SB_REGISTRY_PROJECT_DEVELOP` was deleted on
2026-08-26 while it still looked unreferenced, one commit before the test tier
started using it, and the next push failed.

Genuinely dead, safe to delete (grep the workflow first to confirm nothing
references them):

- `SB_REGISTRY_PROJECT` = `dm-bip` -- old test tier; its SBG repository no
  longer exists
- `SB_REGISTRY_PASSWORD_ERA` (secret) -- superseded by `SB_REGISTRY_PASSWORD`

### Secrets

- `SB_REGISTRY_PASSWORD` -- Registry auth token

## Seven Bridges App Setup

Each deployment tier has a corresponding app on the Seven Bridges platform, whose Docker Repository field points at a registry path:

```
<SB_REGISTRY>/<SB_REGISTRY_USERNAME>/<REGISTRY_PROJECT>/dm-bip-env:<TAG>
```

Concretely, the three tiers publish to:

```
images.sb.biodatacatalyst.nhlbi.nih.gov/<username>/dm-bip-docker-dev/dm-bip-env
images.sb.biodatacatalyst.nhlbi.nih.gov/<username>/dm-bip-develop/dm-bip-env
images.sb.biodatacatalyst.nhlbi.nih.gov/<username>/dm-bip-prod/dm-bip-env
```

### Which app pulls which tag

| App | Pulls | Moves when |
|-----|-------|------------|
| `cc-dm-bip-test` (dev, single consent) | `dm-bip-docker-dev/dm-bip-env:latest` | every push to `docker-dev` |
| `dmc-harmonization-multiconsent-app` (test, cohort mode) | `dm-bip-develop/dm-bip-env:latest` | every push to `docker-push-7bridges` |
| `bdc-dm-bip-prod` (prod) | `dm-bip-prod/dm-bip-env:prod` | a non-rc `bdc-v*` tag is pushed |

That is the current wiring, not a constraint -- any app can be pointed at any
tier by editing its Docker Repository field.

### Tags each build publishes

Every build publishes `:latest` plus an immutable `:sha-<12-char-commit>` tag. A
`bdc-v*` tag build additionally publishes `:bdc-v<X.Y.Z>`, and a **non-rc**
`bdc-v*` build also moves `:prod`.

`:latest` and `:prod` are both moving pointers, overwritten by the next
qualifying push. Pin an SBG app to a `sha-` or `bdc-v` tag when a build must stay
reproducible.

### Image tags are not app revisions

Two independent things can be pinned here, and conflating them is a common
source of "I changed it but nothing happened":

- **Image tag** -- the app's Docker Repository field. Selects which *container*
  the app runs.
- **App revision** -- the trailing `/<N>` on an app ID. Selects which version of
  the *app definition* a task runs against.

Referencing an app without a trailing revision number resolves to its latest
revision, so app revisions can change without breaking clients.
`dm-bip seven-bridges submit --app <id>/<N>` pins an explicit revision when you
need one for testing. Note the interaction: editing the Docker Repository field
creates a new app revision, so an app ID pinned to an older revision keeps
running the old image.

### Deploying to prod

**Prod deploys by moving a tag, not by editing the app.** The `:prod` tag is a
promotion pointer: pushing `bdc-v<X.Y.Z>` builds the image, tags it both
`bdc-v<X.Y.Z>` and `prod`, and the app picks it up on its next run. Pre-release
tags containing `-rc` are excluded from `:prod`, so a release candidate can never
become production.

This means the app definition does not record which version prod is running.
That is recoverable: every run writes `version`, `git_ref`, and `build_date` into
its provenance output. To roll back, re-push `:prod` pointing at the older image
rather than editing the app.

# Release Process

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

Each deployment tier should have a corresponding app on the Seven Bridges platform. The app's Docker Repository field should point to the appropriate registry path:

```
<SB_REGISTRY>/<SB_REGISTRY_USERNAME>/<REGISTRY_PROJECT>/dm-bip-env
```

Concretely, the three tiers publish to:

```
images.sb.biodatacatalyst.nhlbi.nih.gov/<username>/dm-bip-docker-dev/dm-bip-env
images.sb.biodatacatalyst.nhlbi.nih.gov/<username>/dm-bip-develop/dm-bip-env
images.sb.biodatacatalyst.nhlbi.nih.gov/<username>/dm-bip-prod/dm-bip-env
```

Each build publishes `:latest` plus an immutable `:sha-<12-char-commit>` tag;
`bdc-v*` tag builds additionally publish `:bdc-v<X.Y.Z>`. Pin SBG apps to a
`sha-` or `bdc-v` tag when a build must stay reproducible -- `:latest` is
overwritten by the next push to that tier.

When a new image is pushed, update the app revision to pick up the change.

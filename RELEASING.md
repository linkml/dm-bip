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
| Push to `docker-push-7bridges` | `SB_REGISTRY_PROJECT_DEV` | `dm-bip-docker-dev` | `false` | Test: pinned dependency tags, for validation |
| Push `bdc-v*` tag | `SB_REGISTRY_PROJECT_PROD` | `dm-bip-prod` | `false` | Prod: pinned dependency tags, release deployments |

This mapping is implemented in exactly one place: the `Configure build for branch`
step of `.github/workflows/docker-push-7bridges-dev.yml`. There is no other
branch-to-repository logic anywhere in the repo. To retarget a tier, change the
variable value in GitHub -- not the workflow.

**Known issue:** the dev and test tiers currently share `dm-bip-docker-dev`, so
`:latest` in that repository is last-writer-wins between the `docker-dev` and
`docker-push-7bridges` branches. The immutable `sha-<commit>` tags still identify
each build uniquely, so pin SBG apps to a `sha-` tag when it matters. The planned
fix is to point the test tier at `SB_REGISTRY_PROJECT_DEVELOP`
(`dm-bip-develop`), which exists in SBG but which no trigger currently uses.

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

- `SB_REGISTRY` -- Seven Bridges registry hostname (host only, no scheme, no `/v2`)
- `SB_REGISTRY_USERNAME` -- Registry account username; also used as the image
  namespace segment. On a division-scoped BDC account this is the qualified form
  (for example `<user>-<division>`).
- `SB_REGISTRY_PROJECT_DEV` -- Dev and test registry path segment
- `SB_REGISTRY_PROJECT_PROD` -- Prod registry path segment
- `SB_REGISTRY_PROJECT_DEVELOP` -- Reserved for the test tier; not yet wired up,
  see the known issue above

Unused legacy variables, safe to delete: `SB_REGISTRY_PROJECT` (old test tier,
its SBG repo no longer exists), `SB_REGISTRY_PROJECT_RELMAN` (its workflow was
removed), `SB_REGISTRY_USERNAME_ERA` and `SB_REGISTRY_PASSWORD_ERA` (superseded
by `SB_REGISTRY_USERNAME` / `SB_REGISTRY_PASSWORD`).

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
images.sb.biodatacatalyst.nhlbi.nih.gov/<username>/dm-bip-prod/dm-bip-env
```

Each build publishes `:latest` plus an immutable `:sha-<12-char-commit>` tag;
`bdc-v*` tag builds additionally publish `:bdc-v<X.Y.Z>`. Pin SBG apps to a
`sha-` or `bdc-v` tag when a build must stay reproducible -- `:latest` is
overwritten by the next push to that tier.

When a new image is pushed, update the app revision to pick up the change.

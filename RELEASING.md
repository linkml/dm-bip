# Release Process

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

For iterative development. Images are built with `BDC_PULL_LATEST=true`, so external repos (trans-specs, harmonized variables) are cloned at their default branch and can be updated with `git pull` at runtime.

### Test (`docker-push-7bridges` branch)

For pre-release validation of specific studies. Images are built with pinned dependency tags. Push commits to this branch to trigger a build to the test registry.

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

Each deployment tier should have a corresponding app on the Seven Bridges platform. The app's Docker Repository field should point to the appropriate registry path:

```
<SB_REGISTRY>/<SB_REGISTRY_USERNAME>/<REGISTRY_PROJECT>/dm-bip-env
```

When a new image is pushed, update the app revision to pick up the change.

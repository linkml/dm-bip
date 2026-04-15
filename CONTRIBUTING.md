# Contribution Guidelines

When contributing to this repository, please first discuss the changes you wish to make via an [issue](https://github.com/linkml/dm-bip/issues), email, or any other method, with the owners of this repository before issuing a pull request.

## Community Guidelines

We welcome you to our community! We seek to provide a welcoming and safe development experience for everyone. Please read our [code of conduct](CODE_OF_CONDUCT.md) and reach out to us if you have any questions.

## How to contribute

### Reporting bugs or making feature requests

To report a bug or suggest a new feature, please go to the [dm-bip issue tracker](https://github.com/linkml/dm-bip/issues).

Please supply enough details to enable the developers to verify and troubleshoot your issue:

* Provide a clear and descriptive title as well as a concise summary of the issue to identify the problem.
* Describe the exact steps which reproduce the problem in as many details as possible.
* Describe the behavior you observed after following the steps and point out what exactly is the problem with that behavior.
* Explain which behavior you expected to see instead and why.

### The development lifecycle

1. Create a branch from `main` for your bug fix or feature. Name the branch descriptively, e.g., `fix-validation-error` or `add-duckdb-output`.
2. Make sure your branch has the latest commits from `main`.
3. After completing work, run `make test` and `make lint` locally.
4. Push and create a pull request to the `main` branch.

All development must be done on a separate branch — never commit directly to `main`.

> A code review is required before merging.

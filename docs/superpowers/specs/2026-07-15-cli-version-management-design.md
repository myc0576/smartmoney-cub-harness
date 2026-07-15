# CLI Version Management Design

## Goal

Make `smartmoney-cub-harness` a predictable, upgradeable CLI without weakening its offline-first and read-only safety boundaries. Users must be able to identify the installed version, diagnose conflicting launchers, and follow an explicit upgrade path.

## Scope

This change prepares release `0.1.1` and covers:

- one authoritative package version;
- a top-level `smcub --version` command;
- launcher conflict diagnostics in `smcub doctor`;
- isolated installation instructions for Windows and POSIX systems;
- a documented SemVer, Git tag, GitHub Release, and PyPI/pipx lifecycle;
- upgrade instructions for existing Git, pip, pipx, and copied-source users.

Publishing to PyPI is a separate release operation because it requires repository and PyPI Trusted Publishing configuration. This change may document and prepare that workflow, but it must not introduce credentials or claim that a PyPI release exists before one is verified.

## Version Source

The package version will have one source of truth. `pyproject.toml` will obtain the build version from the package version attribute through setuptools dynamic metadata. Runtime output, built distributions, `smcub --version`, and `smcub doctor` will therefore report the same value.

The release prepared by this change is `0.1.1`, a patch release because it improves packaging, diagnostics, and documentation without changing the decision-review contract.

## CLI Behavior

### `smcub --version`

The root argument parser will support:

```text
smcub --version
```

It will print a stable, script-friendly line containing the command name and version, then exit successfully without running a subcommand or using the network.

### `smcub doctor`

The existing doctor payload will retain every current safety and privacy field. It will add a launcher diagnostic object containing only non-sensitive values:

- whether an `smcub` launcher is discoverable on `PATH`;
- how many distinct launchers are discoverable;
- whether multiple launchers create a conflict risk;
- whether the first launcher resolves to the current Python environment.

Doctor must not print launcher paths, Python installation paths, usernames, credentials, or other local identifiers. The existing redaction layer remains in force.

Launcher discovery will be deterministic and independently testable by accepting explicit PATH and platform inputs in a private helper. Duplicate path entries will not inflate the count. Missing launchers will be reported as a valid diagnostic state rather than a doctor failure.

## Installation and Upgrade Model

The preferred end-user installation will be `pipx` once the package is published to PyPI:

```text
pipx install smartmoney-cub-harness
pipx upgrade smartmoney-cub-harness
```

Repository contributors and pre-PyPI users will use an isolated `.venv`. Documentation will avoid relying on an arbitrary global `smcub` executable during setup and will show module-based or environment-qualified commands where appropriate.

Existing users do not update automatically:

- editable Git checkout: `git pull`; reinstall only when packaging metadata or dependencies change;
- pip installation: `python -m pip install --upgrade smartmoney-cub-harness`;
- pipx installation: `pipx upgrade smartmoney-cub-harness`;
- copied source archive: download a new release or migrate to Git/pipx.

There will be no background update check and no `self-update` command. Both would add network behavior or mutate the user's Python environment, contrary to the project's default operating model.

## Release Policy

Versions follow Semantic Versioning:

- patch: compatible fixes, documentation, diagnostics;
- minor: compatible CLI commands or schema capabilities;
- major: incompatible CLI, artifact, or contract changes.

Each public release should follow this order:

1. update the single version source;
2. run the full test and doctor checks;
3. merge the reviewed change;
4. create a matching `vX.Y.Z` Git tag;
5. create a GitHub Release from that tag;
6. publish the same version to PyPI through Trusted Publishing;
7. verify installation in a clean pipx environment.

A version must never be reused after publication. Safety contract changes require explicit release notes even when backward compatible.

## Tests

Implementation will use test-driven development.

Automated coverage will prove:

- `smcub --version` succeeds and reports `0.1.1`;
- runtime and build metadata use the same version source;
- doctor preserves all existing safety fields;
- doctor detects zero, one, duplicate, and multiple launcher cases;
- doctor never exposes the supplied launcher paths;
- both README files contain the supported install and upgrade commands;
- the full existing test suite remains green.

Manual verification will run the installed CLI from an isolated environment, execute `doctor`, execute the toy loop, and confirm `READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE` and `champion_mutated=false` remain present.

## Non-Goals

- automatic background update checks;
- self-modifying or self-updating CLI behavior;
- broker, account, order, or cancellation integration;
- storing credentials for PyPI or GitHub;
- changing the review loop, rule governance, or safety declaration;
- publishing to PyPI before Trusted Publishing is configured and verified.

## Acceptance Criteria

- Version `0.1.1` has exactly one source of truth.
- `smcub --version` works without a subcommand.
- `smcub doctor` reports launcher conflict risk without revealing local paths.
- `.venv/` is ignored.
- Windows, POSIX, pipx, and existing-user upgrade instructions are documented.
- All tests pass on the supported Python versions through CI.
- The toy loop remains offline and does not mutate champion rules.

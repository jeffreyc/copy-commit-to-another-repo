# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.1.0] - 2026-03-08

### Added

* [#1] - add support for copying multiple commits per push

### Fixed

* [#2] - fix KeyError crash when optional env vars are absent
* [#3] - retry push after rebase on non-fast-forward rejection
* [#4] - formatting fixes
* [#5] - fix first commit in a repo being silently skipped
* [#7] - fix several error handling and robustness issues

## [1.0.0] - 2023-04-11

* Initial Release

[unreleased]: https://github.com/jeffreyc/copy-commit-to-another-repo/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/jeffreyc/copy-commit-to-another-repo/releases/tag/v1.1.0
[#7]: https://github.com/jeffreyc/copy-commit-to-another-repo/pull/7
[#5]: https://github.com/jeffreyc/copy-commit-to-another-repo/pull/5
[#4]: https://github.com/jeffreyc/copy-commit-to-another-repo/pull/4
[#3]: https://github.com/jeffreyc/copy-commit-to-another-repo/pull/3
[#2]: https://github.com/jeffreyc/copy-commit-to-another-repo/pull/2
[#1]: https://github.com/jeffreyc/copy-commit-to-another-repo/pull/1
[1.0.0]: https://github.com/jeffreyc/copy-commit-to-another-repo/releases/tag/v1.0.0

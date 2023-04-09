# copy-commit-to-another-repo

`copy-commit-to-another-repo` is a GitHub Action that copies commits from the current repository to another repository.
The intent is to enable keeping two isolated repositories in sync; _e.g._, you have `work` and `home` repositories for your dotfiles, and you want to be able to update either, keeping shared files in sync, including commit messages, while not syncing everything.

## Configuration

### Environment

- `PERSONAL_ACCESS_TOKEN` - this needs to be set under `Settings` -> `Secrets and variables` -> `Actions` -> `New repository secret` on the source repository.
  Create a token under `Settings` -> `Developer settings` -> `Personal access tokens` -> `Tokens (classic)` or `Fine-grained tokens`.
  The token will need `repo` permissions (classic) or `Repository permissions` -> `Contents` permissions (fine-grained).
  
### Inputs

- `destination` - the repository to copy commits to.
- `branch` [optional] - the branch to copy commits to. If unspecified, the default branch for `destination` will be used.
- `include` [optional] - a comma-separated list of [regular expressions](https://docs.python.org/3/howto/regex.html) to match against; e.g., `hello,world?`.
  If specified, only changes to files that match a pattern in `include` will be copied.
  Both `include` and `exclude` may be specified.
  If neither `include` nor `exclude` are specified, all changes will be copied.
- `exclude` [optional] - a comma-separated list of [regular expressions](https://docs.python.org/3/howto/regex.html) to match against; e.g., `hello,world?`.
  If specified, all changes will be copied except changes to files that match a pattern in `exclude`.
  Both `include` and `exclude` may be specified.
  If neither `include` nor `exclude` are specified, all changes will be copied.

## Usage

```yaml
name: Copy Commit

on: push

jobs:
  copy-commit:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v3
        with:
          fetch-depth: 2
      - name: Copy Commit
        uses: jeffreyc/copy-commit-to-another-repo@v1.0.0
        env:
          PERSONAL_ACCESS_TOKEN: ${{ secrets.PERSONAL_ACCESS_TOKEN }}
        with:
          include: 'hello,world?'
          exclude: '"world,"'
          destination: 'jeffreyc/hello-copy'
          branch: 'staging'
```

_n.b._, you must specify `fetch-depth: 2` for the `Checkout` action, else git will be unable to determine what has changed.

## License

`copy-commit-to-another-repo` is released under the [BSD 3-Clause License](LICENSE.md).

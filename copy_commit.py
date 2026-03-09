#!/usr/bin/env python

import csv
import io
import logging
import os
import re
import subprocess
import sys
import tempfile
from typing import Optional, Pattern


class CopyCommit:
    def __init__(self, log_level: int = logging.DEBUG):
        self.logger = self.get_logger(log_level)
        self.cwd = os.environ["GITHUB_WORKSPACE"]

    @staticmethod
    def get_logger(log_level: int = logging.DEBUG) -> logging.Logger:
        logger = logging.getLogger("copy-commit-to-another-repo")
        handler = logging.StreamHandler()
        logger.addHandler(handler)
        logger.setLevel(log_level)
        return logger

    @staticmethod
    def match(item: str, patterns: list[Pattern[str]]) -> bool:
        if [i for i in [p.match(item) for p in patterns] if i is not None]:
            return True
        return False

    def parse_csv(self, to_parse: str) -> list[str]:
        f = io.StringIO(to_parse)
        reader = csv.reader(f, delimiter=",", skipinitialspace=True)
        return (list(reader) or [[]])[0]

    def require(self, var: str, name: str) -> str:
        if not os.environ.get(var):
            self.logger.critical(f"{name} must be specified")
            sys.exit(1)
        return os.environ[var].strip()

    def run(self, cmd: str, cwd: Optional[str] = None) -> str:
        self.logger.info(f"Running `{cmd}` in `{cwd or self.cwd}`")
        try:
            ret = subprocess.check_output(
                cmd, stderr=subprocess.STDOUT, shell=True, cwd=cwd
            ).decode("utf-8")
        except subprocess.CalledProcessError as e:
            self.logger.critical(
                f"Exception on process, rc={e.returncode}, output={e.output}"
            )
            raise
        self.logger.info(ret)
        return ret

    def main(self) -> None:
        token = self.require("PERSONAL_ACCESS_TOKEN", "PERSONAL_ACCESS_TOKEN")
        destination = self.require("INPUT_DESTINATION", "destination")

        self.run(f"git config --global --add safe.directory {self.cwd}")

        before = os.environ.get("GITHUB_EVENT_BEFORE", "")
        zero_sha = "0" * 40
        if before and before != zero_sha:
            commits = self.run(
                f"git log --pretty=format:%H --reverse {before}..HEAD"
            ).split()
        else:
            commits = self.run("git log --pretty=format:%H -1").split()

        self.logger.debug(f"commits to process: {commits}")

        if not commits:
            self.logger.info("No commits in range, nothing to apply.")
            return

        excluded = [
            re.compile(pattern)
            for pattern in self.parse_csv(os.environ.get("INPUT_EXCLUDE", ""))
            if pattern
        ]
        self.logger.debug(f"excluded: {excluded}")
        included = [
            re.compile(pattern)
            for pattern in self.parse_csv(os.environ.get("INPUT_INCLUDE", ""))
            if pattern
        ]
        self.logger.debug(f"included: {included}")

        with tempfile.TemporaryDirectory() as tmpdir:
            branch = os.environ.get("INPUT_BRANCH")
            if branch:
                self.run(
                    f'git clone --single-branch --branch {branch} "https://x-access-token:{token}@github.com/{destination}.git" "{tmpdir}"'
                )
            else:
                self.run(
                    f'git clone --single-branch "https://x-access-token:{token}@github.com/{destination}.git" "{tmpdir}"'
                )

            applied = False
            for sha in commits:
                username = self.run(f"git log --pretty=format:%an -1 {sha}")
                self.run(f'git config --global user.name "{username}"')

                email = self.run(f"git log --pretty=format:%ae -1 {sha}")
                self.run(f'git config --global user.email "{email}"')

                modified = self.run(
                    f"git diff-tree --no-commit-id --name-only --root {sha} -r"
                ).split()
                self.logger.debug(f"commit {sha} modified: {modified}")

                keep = []
                for item in modified:
                    if (not included or self.match(item, included)) and (
                        not excluded or not self.match(item, excluded)
                    ):
                        keep.append(item)

                self.logger.debug(f"commit {sha} keep: {keep}")

                if keep:
                    keep_str = " ".join(keep)
                    try:
                        self.run(
                            f"git --git-dir={self.cwd}/.git format-patch -k -1 --stdout {sha} -- {keep_str} | git am -3 -k",
                            tmpdir,
                        )
                    except subprocess.CalledProcessError:
                        self.run("git am --abort", tmpdir)
                        raise
                    applied = True
                else:
                    self.logger.info(
                        f"Commit {sha}: all files excluded or no files included, skipping."
                    )

            if applied:
                self.run("git log -2", tmpdir)
                try:
                    self.run("git push -u origin", tmpdir)
                except subprocess.CalledProcessError:
                    self.logger.info("Push failed, pulling and retrying...")
                    self.run("git pull --rebase", tmpdir)
                    self.run("git push -u origin", tmpdir)


if __name__ == "__main__":
    cc = CopyCommit()
    cc.main()

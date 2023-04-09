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
        reader = csv.reader(f, delimiter=",")
        return (list(reader) or [[]])[0]

    def require(self, var: str, name: str) -> str:
        if not os.environ[var]:
            self.logger.critical(f"{name} must be specified")
            sys.exit(1)
        return os.environ[var].strip()

    def run(self, cmd: str, cwd: Optional[str] = None) -> str:
        self.logger.info(f"Running `{cmd}` in `{cwd or self.cwd}`")
        try:
            ret = subprocess.check_output(
                cmd, stderr=subprocess.STDOUT, shell=True, cwd=cwd
            ).decode("ascii")
        except subprocess.CalledProcessError as e:
            self.logger.critical(
                "Exception on process, rc=", e.returncode, "output=", e.output
            )
            raise
        self.logger.info(ret)
        return ret

    def main(self) -> None:
        token = self.require("PERSONAL_ACCESS_TOKEN", "PERSONAL_ACCESS_TOKEN")
        destination = self.require("INPUT_DESTINATION", "destination")

        self.run(f"git config --global --add safe.directory {self.cwd}")

        username = self.run("git log --pretty=format:%an -1")
        self.run(f'git config --global user.name "{username}"')

        email = self.run("git log --pretty=format:%ae -1")
        self.run(f'git config --global user.email "{email}"')

        excluded = [
            re.compile(pattern)
            for pattern in self.parse_csv(os.environ["INPUT_EXCLUDE"])
            if pattern
        ]
        self.logger.debug(f"excluded: {excluded}")
        included = [
            re.compile(pattern)
            for pattern in self.parse_csv(os.environ["INPUT_INCLUDE"])
            if pattern
        ]
        self.logger.debug(f"included: {included}")

        with tempfile.TemporaryDirectory() as tmpdir:
            if os.environ["INPUT_BRANCH"]:
                branch = os.environ["INPUT_BRANCH"]
                self.run(
                    f'git clone --single-branch --branch {branch} "https://x-access-token:{token}@github.com/{destination}.git" "{tmpdir}"'
                )
            else:
                self.run(
                    f'git clone --single-branch "https://x-access-token:{token}@github.com/{destination}.git" "{tmpdir}"'
                )

            modified = self.run(
                f"git diff-tree --no-commit-id --name-only HEAD -r"
            ).split()

            self.logger.debug(f"modified: {modified}")

            keep = []
            for item in modified:
                if (not included or self.match(item, included)) and (
                    not excluded or not self.match(item, excluded)
                ):
                    keep.append(item)

            self.logger.debug(f"keep: {keep}")

            if keep:
                keep = " ".join(keep)
                self.run(
                    f"git --git-dir={self.cwd}/.git format-patch -k -1 --stdout HEAD -- {keep} | git am -3 -k",
                    tmpdir,
                )
                self.run("git log -2", tmpdir)
                self.run("git push -u origin", tmpdir)
            else:
                self.logger.info(
                    "All files excluded or no files included, nothing to apply."
                )


if __name__ == "__main__":
    cc = CopyCommit()
    cc.main()

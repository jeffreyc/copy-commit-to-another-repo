#!/usr/bin/env python

import csv
import io
import json
import logging
import os
import re
import shlex
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

    def is_duplicate(self, sha: str, dest_dir: str) -> bool:
        """Check if a commit with matching metadata already exists in destination."""
        source_info = self.run(
            f"git log --pretty=format:%an%x00%ae%x00%aI%x00%s -1 {sha}"
        )
        parts = source_info.split("\x00")
        if len(parts) != 4:
            return False
        author_name, author_email, author_date, subject = parts

        matches = self.run(
            f"git log --all --pretty=format:%an%x00%ae%x00%aI%x00%s%x00%x00"
            f" --fixed-strings --grep={shlex.quote(subject)}"
            f" --author={shlex.quote(author_email)}",
            dest_dir,
        ).strip()

        if not matches:
            return False

        for entry in matches.split("\x00\x00"):
            entry = entry.strip()
            if not entry:
                continue
            entry_parts = entry.split("\x00")
            if len(entry_parts) != 4:
                continue
            dest_name, dest_email, dest_date, dest_subject = entry_parts
            if (
                dest_name == author_name
                and dest_email == author_email
                and dest_date == author_date
                and dest_subject == subject
            ):
                return True

        return False

    def main(self) -> None:
        token = self.require("PERSONAL_ACCESS_TOKEN", "PERSONAL_ACCESS_TOKEN")
        destination = self.require("INPUT_DESTINATION", "destination")

        self.run(f"git config --global --add safe.directory {self.cwd}")

        before = os.environ.get("GITHUB_EVENT_BEFORE", "")
        if not before:
            event_path = os.environ.get("GITHUB_EVENT_PATH", "")
            if event_path and os.path.isfile(event_path):
                with open(event_path) as f:
                    before = json.load(f).get("before", "")
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
                    try:
                        if self.is_duplicate(sha, tmpdir):
                            self.logger.info(
                                f"Commit {sha}: already exists in destination, skipping."
                            )
                            continue
                    except subprocess.CalledProcessError:
                        self.logger.info(
                            f"Commit {sha}: duplicate check failed, proceeding with copy."
                        )

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

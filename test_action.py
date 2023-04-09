#!/usr/bin/env python

import logging
import os
import unittest

import copy_commit


class TestAction(unittest.TestCase):
    def setUp(self):
        self.cc = copy_commit.CopyCommit(logging.CRITICAL)
        self.repo_path = os.path.join(os.environ["GITHUB_WORKSPACE"], "test")
        self.sha = os.environ["GITHUB_SHA"]

    def get_changed_files(self, rev):
        return self.cc.run(
            f"git diff-tree --no-commit-id --name-only {rev} -r", self.repo_path
        ).split()

    def test_branch(self):
        # HEAD..HEAD~1 on <branch>
        pass

    def test_exclude(self):
        changed = self.get_changed_files("HEAD~1..HEAD~2")
        self.assertIn(f"{self.sha}-exclude-2", changed)

    def test_include(self):
        changed = self.get_changed_files("HEAD~2..HEAD~3")
        self.assertIn(f"{self.sha}-include-1", changed)
        self.assertIn(f"{self.sha}-include-2", changed)

    def test_include_and_exclude(self):
        changed = self.get_changed_files("HEAD..HEAD~1")
        self.assertIn(f"{self.sha}-include-and-exclude-2", changed)

    def test_no_args(self):
        changed = self.get_changed_files("HEAD~3..HEAD~4")
        self.assertIn(f"{self.sha}-no-args-1", changed)
        self.assertIn(f"{self.sha}-no-args-2", changed)
        author = self.cc.run("git log --format='%an <%ae>' -1 HEAD~3", self.repo_path).strip()
        self.assertEqual("Test User <user@host.domain>", author)
        raw_body = self.cc.run("git log --format='%B' -1 HEAD~3", self.repo_path).strip()
        self.assertEqual("test no-args", raw_body)


if __name__ == "__main__":
    unittest.main()

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
            f"git diff-tree --no-commit-id --name-only --root {rev} -r", self.repo_path
        ).split()

    def test_branch(self):
        # HEAD..HEAD~1 on <branch>
        pass

    def test_different_authors(self):
        author = self.cc.run("git log --format='%an <%ae>' -1 HEAD~5", self.repo_path).strip()
        self.assertEqual("Alternate User <alternate@host.domain>", author)
        changed = self.get_changed_files("HEAD~5")
        self.assertIn(f"{self.sha}-different-authors-1", changed)
        author = self.cc.run("git log --format='%an <%ae>' -1 HEAD~4", self.repo_path).strip()
        self.assertEqual("Test User <user@host.domain>", author)
        changed = self.get_changed_files("HEAD~4")
        self.assertIn(f"{self.sha}-different-authors-2", changed)

    def test_exclude(self):
        changed = self.get_changed_files("HEAD~1")
        self.assertIn(f"{self.sha}-exclude-2", changed)

    def test_include(self):
        changed = self.get_changed_files("HEAD~2")
        self.assertIn(f"{self.sha}-include-1", changed)
        self.assertIn(f"{self.sha}-include-2", changed)

    def test_include_and_exclude(self):
        changed = self.get_changed_files("HEAD")
        self.assertIn(f"{self.sha}-include-and-exclude-2", changed)

    def test_multiple_commits(self):
        changed = self.get_changed_files("HEAD~6")
        self.assertIn(f"{self.sha}-multiple-commits-1", changed)
        self.assertIn(f"{self.sha}-multiple-commits-3", changed)
        contents = self.cc.run(f"git show HEAD~6:{self.sha}-multiple-commits-1", self.repo_path).strip()
        self.assertEqual("multiple-commits-1b", contents)
        changed = self.get_changed_files("HEAD~7")
        self.assertIn(f"{self.sha}-multiple-commits-1", changed)
        self.assertIn(f"{self.sha}-multiple-commits-2", changed)
        contents = self.cc.run(f"git show HEAD~7:{self.sha}-multiple-commits-1", self.repo_path).strip()
        self.assertEqual("multiple-commits-1a", contents)

    def test_nonexistent_before(self):
        result = self.cc.run(
            f"git log --pretty=format:%H -- {self.sha}-nonexistent-before",
            self.repo_path
        ).strip()
        self.assertEqual("", result)

    def test_no_args(self):
        changed = self.get_changed_files("HEAD~9")
        self.assertIn(f"{self.sha}-no-args-1", changed)
        self.assertIn(f"{self.sha}-no-args-2", changed)
        author = self.cc.run("git log --format='%an <%ae>' -1 HEAD~9", self.repo_path).strip()
        self.assertEqual("Test User <user@host.domain>", author)
        raw_body = self.cc.run("git log --format='%B' -1 HEAD~9", self.repo_path).strip()
        self.assertEqual("test no-args", raw_body)

    def test_partial_filter(self):
        changed = self.get_changed_files("HEAD~3")
        self.assertIn(f"{self.sha}-partial-filter-1", changed)
        self.assertNotIn(f"{self.sha}-partial-filter-2", changed)

    def test_zero_sha(self):
        changed = self.get_changed_files("HEAD~8")
        self.assertIn(f"{self.sha}-zero-sha-2", changed)
        self.assertNotIn(f"{self.sha}-zero-sha-1", changed)


if __name__ == "__main__":
    unittest.main()

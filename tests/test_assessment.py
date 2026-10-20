"""The assessment check: full coverage, recommendations for gaps, and no finding without retrieved provision text."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "skills" / "singapore-pdpa-assessment"
SCRIPT = SKILL / "scripts" / "assessment.py"
SUBJECT = ("SYNTHETIC feature: a retailer's app collects customers' names and phone numbers at sign-up "
           "and shares them with an overseas analytics vendor. No retention period is stated.")


class AssessmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.run_dir = self.base / "run"
        self.call("init", self.run_dir, "--subject", SUBJECT, "--subject-reference", "Synthetic product brief",
                  "--law-as-at", "2026-10-20", "--items", "transfer,retention,do-not-call")
        self.call("add-standard", self.run_dir, "--name", "Personal Data Protection Act 2012", "--kind", "legislation",
                  "--version", "SYNTHETIC version label", "--how", "Fixture")
        (self.base / "s26.txt").write_text("SYNTHETIC placeholder for retrieved section 26 text.", encoding="utf-8")

    def call(self, *args, expect=0):
        process = subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True)
        self.assertEqual(process.returncode, expect, process.stdout + process.stderr)
        return json.loads(process.stdout)

    def finding(self, item, assessment, ref, **extra):
        args = ["finding", self.run_dir, "--item", item, "--assessment", assessment, "--severity", "high",
                "--standard-ref", ref, "--explanation", "Synthetic explanation."]
        for key, value in extra.items():
            args += [f"--{key}", value]
        return self.call(*args)

    def complete(self):
        self.call("add-provision", self.run_dir, "--section", "26", "--file", self.base / "s26.txt",
                  "--version", "SYNTHETIC", "--how", "Fixture")
        (self.base / "s25.txt").write_text("SYNTHETIC placeholder for section 25.", encoding="utf-8")
        self.call("add-provision", self.run_dir, "--section", "25", "--file", self.base / "s25.txt",
                  "--version", "SYNTHETIC", "--how", "Fixture")
        self.finding("transfer", "gap", "s 26(1)", recommendation="Synthetic recommendation.",
                     quote="shares them with an overseas analytics vendor")
        self.finding("retention", "risk", "s 25", recommendation="Synthetic recommendation.")
        self.finding("do-not-call", "not-applicable", "Part 9")

    def test_checklist_items_exist_in_the_reference(self):
        items = json.loads((SKILL / "references" / "obligations.json").read_text(encoding="utf-8"))["items"]
        self.assertIn("part-6b-status", {i["id"] for i in items})
        self.assertTrue(all(i["sections"] or i["schedules"] for i in items))

    def test_complete_assessment_passes_and_exports(self):
        self.complete()
        self.assertEqual(self.call("check", self.run_dir)["status"], "pass")
        exported = self.call("export", self.run_dir)
        self.assertEqual(exported["coverage"], {"items_total": 3, "items_addressed": 3, "not_addressed": []})
        self.assertEqual(exported["record"]["status"], "pass")

    def test_finding_without_retrieved_provision_text_fails(self):
        self.finding("transfer", "gap", "s 26(1)", recommendation="x")
        self.assertIn("relies on s 26 without its retrieved text", " ".join(self.call("check", self.run_dir, expect=1)["errors"]))

    def test_schedule_references_need_their_text_too(self):
        self.finding("transfer", "risk", "s 26 read with the First Schedule", recommendation="x")
        errors = " ".join(self.call("check", self.run_dir, expect=1)["errors"])
        self.assertIn("First Schedule without its retrieved text", errors)

    def test_gap_without_recommendation_unaddressed_item_and_false_quote_fail(self):
        self.call("add-provision", self.run_dir, "--section", "26", "--file", self.base / "s26.txt",
                  "--version", "SYNTHETIC", "--how", "Fixture")
        self.finding("transfer", "gap", "s 26", quote="encrypts all data")
        errors = " ".join(self.call("check", self.run_dir, expect=1)["errors"])
        self.assertIn("a gap needs a recommendation", errors)
        self.assertIn("quoted text does not appear in the subject", errors)
        self.assertIn("retention: not addressed", errors)

    def test_act_version_must_be_recorded(self):
        run = self.base / "other"
        self.call("init", run, "--subject", SUBJECT, "--subject-reference", "x", "--law-as-at", "2026-10-20", "--items", "do-not-call")
        self.call("finding", run, "--item", "do-not-call", "--assessment", "not-applicable", "--severity", "info",
                  "--standard-ref", "Part 9", "--explanation", "No messages are sent.")
        self.assertIn("record the Personal Data Protection Act 2012", " ".join(self.call("check", run, expect=1)["errors"]))

    def test_unknown_items_and_bad_sections_are_usage_errors(self):
        self.call("init", self.base / "x", "--subject", "s", "--subject-reference", "r", "--law-as-at", "2026-10-20",
                  "--items", "not-an-item", expect=2)
        self.call("add-provision", self.run_dir, "--section", "section twenty", "--file", self.base / "s26.txt",
                  "--version", "v", "--how", "h", expect=2)


if __name__ == "__main__":
    unittest.main()

import datetime
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import ferment_lib as lib


FIXTURE_RECIPE = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "recipes"
    / "example-ferment"
    / "recipe.md"
)

RECIPES_DIR = Path(__file__).resolve().parent.parent / "recipes"


class RecipesDirectoryTests(unittest.TestCase):
    """Every recipe under recipes/ must parse and compute a schedule.

    Guards against a malformed recipe (bad frontmatter, unsupported schedule
    entry, ...) reaching the repo and CI.
    """

    def test_all_recipes_parse_and_schedule(self):
        recipe_files = sorted(RECIPES_DIR.glob("*/recipe.md"))
        self.assertTrue(recipe_files, "no recipes found under recipes/")
        start = datetime.date(2024, 1, 10)
        for recipe_file in recipe_files:
            with self.subTest(recipe=recipe_file.parent.name):
                recipe = lib.parse_recipe(recipe_file.read_text())
                self.assertTrue(recipe.get("title"), "recipe has no title")
                self.assertIn("schedule", recipe)
                steps = lib.compute_schedule(recipe["schedule"], start)
                self.assertTrue(steps, "recipe schedule produced no steps")


class ParseRecipeTests(unittest.TestCase):
    def test_parses_fixture_recipe(self):
        text = FIXTURE_RECIPE.read_text()
        recipe = lib.parse_recipe(text)
        self.assertEqual(recipe["title"], "Fictional Test Ferment")
        self.assertEqual(recipe["source"]["book"], "The Imaginary Fermenter's Companion")
        self.assertEqual(recipe["source"]["page"], "17")
        self.assertEqual(recipe["yield"], "1 liter")
        self.assertEqual(len(recipe["schedule"]), 3)
        self.assertIn("Ingredients", recipe["body"])

    def test_missing_frontmatter_raises(self):
        with self.assertRaises(ValueError):
            lib.parse_recipe("no frontmatter here")


class ComputeScheduleTests(unittest.TestCase):
    def setUp(self):
        self.start = datetime.date(2024, 1, 10)

    def test_single_day_step(self):
        schedule = [{"day": "0", "task": "Mix"}]
        steps = lib.compute_schedule(schedule, self.start)
        self.assertEqual(steps, [lib.Step(date=self.start, task="Mix")])

    def test_day_range_repeats_daily_inclusive(self):
        schedule = [{"days": "1-3", "task": "Burp"}]
        steps = lib.compute_schedule(schedule, self.start)
        expected_dates = [
            self.start + datetime.timedelta(days=d) for d in (1, 2, 3)
        ]
        self.assertEqual([s.date for s in steps], expected_dates)
        self.assertTrue(all(s.task == "Burp" for s in steps))

    def test_mixed_schedule_sorted_by_date(self):
        schedule = [
            {"day": "7", "task": "Bottle"},
            {"day": "0", "task": "Mix"},
            {"days": "1-2", "task": "Burp"},
        ]
        steps = lib.compute_schedule(schedule, self.start)
        self.assertEqual(
            [s.date for s in steps],
            [
                self.start,
                self.start + datetime.timedelta(days=1),
                self.start + datetime.timedelta(days=2),
                self.start + datetime.timedelta(days=7),
            ],
        )

    def test_missing_day_and_days_raises(self):
        with self.assertRaises(ValueError):
            lib.compute_schedule([{"task": "oops"}], self.start)

    def test_full_fixture_schedule(self):
        recipe = lib.parse_recipe(FIXTURE_RECIPE.read_text())
        steps = lib.compute_schedule(recipe["schedule"], self.start)
        # day 0, days 1-6 (6 steps), day 7 => 8 steps total
        self.assertEqual(len(steps), 8)
        self.assertEqual(steps[0].date, self.start)
        self.assertEqual(steps[-1].date, self.start + datetime.timedelta(days=7))


class RenderChecklistTests(unittest.TestCase):
    def test_render_checklist_format(self):
        steps = [
            lib.Step(date=datetime.date(2024, 1, 10), task="Mix"),
            lib.Step(date=datetime.date(2024, 1, 11), task="Burp"),
        ]
        rendered = lib.render_checklist(steps)
        self.assertEqual(
            rendered,
            "- [ ] 2024-01-10: Mix\n- [ ] 2024-01-11: Burp",
        )


class StepsDueOnTests(unittest.TestCase):
    def test_filters_by_date(self):
        d1 = datetime.date(2024, 1, 10)
        d2 = datetime.date(2024, 1, 11)
        steps = [lib.Step(date=d1, task="A"), lib.Step(date=d2, task="B")]
        self.assertEqual(lib.steps_due_on(steps, d1), [steps[0]])
        self.assertEqual(lib.steps_due_on(steps, d2), [steps[1]])
        self.assertEqual(
            lib.steps_due_on(steps, datetime.date(2024, 1, 12)), []
        )


class BatchMarkerTests(unittest.TestCase):
    def test_round_trip(self):
        start = datetime.date(2024, 1, 10)
        marker = lib.render_batch_marker("example-ferment", start)
        slug, parsed_start = lib.parse_batch_marker(marker)
        self.assertEqual(slug, "example-ferment")
        self.assertEqual(parsed_start, start)

    def test_missing_marker_raises(self):
        with self.assertRaises(ValueError):
            lib.parse_batch_marker("no marker here")

    def test_render_batch_body_contains_marker_and_checklist(self):
        start = datetime.date(2024, 1, 10)
        steps = [lib.Step(date=start, task="Mix")]
        body = lib.render_batch_body("example-ferment", start, steps)
        slug, parsed_start = lib.parse_batch_marker(body)
        self.assertEqual(slug, "example-ferment")
        self.assertEqual(parsed_start, start)
        self.assertIn("- [ ] 2024-01-10: Mix", body)


class ChecklistLineTests(unittest.TestCase):
    def test_checked_detection(self):
        self.assertTrue(lib.checklist_line_checked("- [x] 2024-01-10: Mix"))
        self.assertTrue(lib.checklist_line_checked("- [X] 2024-01-10: Mix"))
        self.assertFalse(lib.checklist_line_checked("- [ ] 2024-01-10: Mix"))

    def test_parse_checklist_date(self):
        self.assertEqual(
            lib.parse_checklist_date("- [ ] 2024-01-10: Mix"),
            datetime.date(2024, 1, 10),
        )
        self.assertIsNone(lib.parse_checklist_date("not a checklist line"))


class BatchIdentityTests(unittest.TestCase):
    def test_form_body_without_label_is_batch(self):
        body = (
            "### Recipe slug\n\nsauerkraut\n\n"
            "### Start date\n\ntoday\n"
        )
        self.assertEqual(
            lib.parse_batch_identity(body),
            {"slug": "sauerkraut", "start": "today"},
        )

    def test_marker_body_is_batch(self):
        start = datetime.date(2024, 1, 10)
        body = lib.render_batch_body(
            "example-ferment",
            start,
            [lib.Step(date=start, task="Mix")],
        )
        self.assertEqual(
            lib.parse_batch_identity(body),
            {"slug": "example-ferment", "start": "2024-01-10"},
        )

    def test_foreign_body_is_not_batch(self):
        body = (
            "### Something else\n\nhello\n\n"
            "This is a regular bug report, not a batch.\n"
        )
        self.assertIsNone(lib.parse_batch_identity(body))


class FormBodyTests(unittest.TestCase):
    def test_parses_headings_and_values(self):
        body = (
            "### Recipe slug\n\nsauerkraut\n\n"
            "### Start date\n\ntoday\n"
        )
        fields = lib.parse_form_body(body)
        self.assertEqual(fields["Recipe slug"], "sauerkraut")
        self.assertEqual(fields["Start date"], "today")

    def test_no_response_becomes_empty(self):
        body = "### Start date\n\n_No response_\n"
        fields = lib.parse_form_body(body)
        self.assertEqual(fields["Start date"], "")


class ReminderMarkerTests(unittest.TestCase):
    def test_detects_existing_marker_for_date(self):
        date = datetime.date(2024, 1, 10)
        marker = lib.render_reminder_marker(date)
        self.assertTrue(lib.has_reminder_for_date(["unrelated", marker], date))
        self.assertFalse(
            lib.has_reminder_for_date(["unrelated"], date)
        )

    def test_different_date_not_matched(self):
        date = datetime.date(2024, 1, 10)
        other = lib.render_reminder_marker(datetime.date(2024, 1, 11))
        self.assertFalse(lib.has_reminder_for_date([other], date))


if __name__ == "__main__":
    unittest.main()

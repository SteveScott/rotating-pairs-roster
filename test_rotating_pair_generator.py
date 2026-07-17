import importlib.util
import pathlib
import subprocess
import sys
import tempfile
import unittest


MODULE_PATH = pathlib.Path(__file__).with_name("rotating-pair-generator.py")
SPEC = importlib.util.spec_from_file_location("rotating_pair_generator", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RotatingPairTests(unittest.TestCase):
    def test_cli_counter_argument_overrides_default(self):
        result = subprocess.run(
            [sys.executable, str(MODULE_PATH), "1"],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("requested counter = 1", result.stdout)

    def test_cli_invalid_counter_reports_error(self):
        result = subprocess.run(
            [sys.executable, str(MODULE_PATH), "not-a-number"],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("ERROR: Counter must be an integer", result.stdout)

    def test_even_roster_counter_zero(self):
        men = ["A", "B", "C", "D", "E", "F"]
        pairs = MODULE.rotated_pairs(men, 0)
        self.assertEqual(pairs, [("A", "F"), ("B", "E"), ("C", "D")])

    def test_even_roster_rotates_with_counter(self):
        men = ["A", "B", "C", "D", "E", "F"]
        pairs_0 = MODULE.rotated_pairs(men, 0)
        pairs_1 = MODULE.rotated_pairs(men, 1)
        pairs_2 = MODULE.rotated_pairs(men, 2)

        self.assertNotEqual(pairs_0, pairs_1)
        self.assertNotEqual(pairs_1, pairs_2)

    def test_even_cycle_modulo_behavior(self):
        men = ["A", "B", "C", "D", "E", "F"]
        # For even n, cycle length is n - 1.
        self.assertEqual(MODULE.rotated_pairs(men, 5), MODULE.rotated_pairs(men, 0))

    def test_even_each_man_gets_unique_partners_over_cycle(self):
        men = ["A", "B", "C", "D", "E", "F"]
        cycle_len = len(men) - 1
        partners = {m: set() for m in men}

        for counter in range(cycle_len):
            for a, b in MODULE.rotated_pairs(men, counter):
                partners[a].add(b)
                partners[b].add(a)

        for m in men:
            self.assertEqual(len(partners[m]), len(men) - 1)

    def test_odd_cycle_modulo_behavior(self):
        men = ["A", "B", "C", "D", "E"]
        # For odd n, cycle length is n (because of one bye per round).
        self.assertEqual(MODULE.rotated_pairs(men, 5), MODULE.rotated_pairs(men, 0))

    def test_odd_pairs_change_with_rotation(self):
        men = ["A", "B", "C", "D", "E"]
        pairs_0 = MODULE.rotated_pairs(men, 0)
        pairs_1 = MODULE.rotated_pairs(men, 1)
        self.assertNotEqual(pairs_0, pairs_1)

    def test_odd_no_one_sits_out(self):
        men = ["A", "B", "C", "D", "E"]
        for counter in range(len(men)):
            seen = set()
            for a, b in MODULE.rotated_pairs(men, counter):
                self.assertNotEqual(a, b)
                seen.add(a)
                seen.add(b)
            self.assertEqual(seen, set(men))

    def test_odd_double_up_rotates_over_full_cycle(self):
        men = ["A", "B", "C", "D", "E"]
        doubled_each_round = []

        for counter in range(len(men)):
            counts = {m: 0 for m in men}
            for a, b in MODULE.rotated_pairs(men, counter):
                counts[a] += 1
                counts[b] += 1

            doubled = [m for m, c in counts.items() if c == 2]
            self.assertEqual(len(doubled), 1)
            doubled_each_round.append(doubled[0])

        self.assertEqual(set(doubled_each_round), set(men))

    def test_full_counter_sweep_all_meet_all_and_no_self_pair(self):
        men = MODULE.load_roster(MODULE.ROSTER_FILE)
        partners = {m: set() for m in men}

        # Sweep through the full roster-sized counter range as requested.
        for counter in range(len(men)):
            for a, b in MODULE.rotated_pairs(men, counter):
                self.assertNotEqual(a, b)
                partners[a].add(b)
                partners[b].add(a)

        for m in men:
            expected_partners = set(men) - {m}
            self.assertEqual(partners[m], expected_partners)

    def test_missing_roster_txt_reports_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            missing_file = pathlib.Path(tmp_dir) / "roster.txt"
            with self.assertRaises(FileNotFoundError) as ctx:
                MODULE.load_roster(missing_file)

            self.assertIn("Roster file not found", str(ctx.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


MODULE_PATH = Path(__file__).with_name('rotating-pair-generator.py')
SPEC = importlib.util.spec_from_file_location('pair_generator', MODULE_PATH)
pair_generator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pair_generator)


class RotatedPairsTests(unittest.TestCase):
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
        pairs = pair_generator.rotated_pairs(men, 0)
        self.assertEqual(pairs, [("A", "F"), ("B", "E"), ("C", "D")])


    def test_even_roster_rotates_with_counter(self):
        men = ["A", "B", "C", "D", "E", "F"]
        pairs_0 = pair_generator.rotated_pairs(men, 0)
        pairs_1 = pair_generator.rotated_pairs(men, 1)
        pairs_2 = pair_generator.rotated_pairs(men, 2)


        self.assertNotEqual(pairs_0, pairs_1)
        self.assertNotEqual(pairs_1, pairs_2)


    def test_even_cycle_modulo_behavior(self):
        men = ["A", "B", "C", "D", "E", "F"]
        # For even n, cycle length is n - 1.
        self.assertEqual(
            pair_generator.rotated_pairs(men, 5),
            pair_generator.rotated_pairs(men, 0),
        )


    def test_even_each_man_gets_unique_partners_over_cycle(self):
        men = ["A", "B", "C", "D", "E", "F"]
        cycle_len = len(men) - 1
        partners = {m: set() for m in men}


        for counter in range(cycle_len):
            for a, b in pair_generator.rotated_pairs(men, counter):
                partners[a].add(b)
                partners[b].add(a)


        for m in men:
            self.assertEqual(len(partners[m]), len(men) - 1)


    def test_odd_cycle_modulo_behavior(self):
        men = ["A", "B", "C", "D", "E"]
        # For odd n, cycle length is n (because of one double-up per round).
        self.assertEqual(
            pair_generator.rotated_pairs(men, 5),
            pair_generator.rotated_pairs(men, 0),
        )


    def test_odd_pairs_change_with_rotation(self):
        men = ["A", "B", "C", "D", "E"]
        pairs_0 = pair_generator.rotated_pairs(men, 0)
        pairs_1 = pair_generator.rotated_pairs(men, 1)
        self.assertNotEqual(pairs_0, pairs_1)


    def test_odd_no_one_sits_out(self):
        men = ["A", "B", "C", "D", "E"]
        for counter in range(len(men)):
            seen = set()
            for a, b in pair_generator.rotated_pairs(men, counter):
                self.assertNotEqual(a, b)
                seen.add(a)
                seen.add(b)
            self.assertEqual(seen, set(men))


    def test_odd_roster_has_one_double_up_each_week(self):
        men = ["A", "B", "C", "D", "E"]


        for counter in range(len(men)):
            counts = {m: 0 for m in men}
            for a, b in pair_generator.rotated_pairs(men, counter):
                counts[a] += 1
                counts[b] += 1


            doubled = [m for m, c in counts.items() if c == 2]
            self.assertEqual(len(doubled), 1)


    def test_full_counter_sweep_all_meet_all_and_no_self_pair(self):
        men = [f"Person {number}" for number in range(1, 10)]
        partners = {m: set() for m in men}


        # Sweep through the full roster-sized counter range as requested.
        for counter in range(len(men)):
            for a, b in pair_generator.rotated_pairs(men, counter):
                self.assertNotEqual(a, b)
                partners[a].add(b)
                partners[b].add(a)


        for m in men:
            expected_partners = set(men) - {m}
            self.assertEqual(partners[m], expected_partners)


    def test_missing_roster_txt_reports_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            missing_file = Path(tmp_dir) / "roster.txt"
            with self.assertRaises(FileNotFoundError) as ctx:
                pair_generator.load_roster(missing_file)


            self.assertIn("Roster file not found", str(ctx.exception))

    def test_odd_roster_has_no_repeated_pair_in_adjacent_weeks(self):
        men = [f"Person {number}" for number in range(1, 10)]
        weeks = [
            {frozenset(pair) for pair in pair_generator.rotated_pairs(men, week)}
            for week in range(len(men))
        ]

        for week, pairs in enumerate(weeks):
            self.assertEqual(len(pairs), len(pair_generator.rotated_pairs(men, week)))
            self.assertFalse(pairs & weeks[week - 1])

    def test_even_roster_has_no_repeated_pair_in_adjacent_weeks(self):
        men = ['A', 'B', 'C', 'D', 'E', 'F']
        weeks = [
            {frozenset(pair) for pair in pair_generator.rotated_pairs(men, week)}
            for week in range(len(men) - 1)
        ]

        for week, pairs in enumerate(weeks):
            self.assertFalse(pairs & weeks[week - 1])


class OddRosterDoubleUpTests(unittest.TestCase):
    """Pin down the odd-roster rule: nobody sits out, so one man doubles up.

    A pair needs two men, so an odd roster cannot leave one man over — a group
    of one is not a pair. Rather than giving that man a bye, the generator pairs
    him a second time with another man from the same week. A name appearing
    twice in a week's output is therefore intended behaviour, not a bug.

    Real roster names are confidential and must never appear in this repository,
    so these tests use placeholder names.
    """

    ODD_ROSTER = [f"Person {number}" for number in range(1, 10)]

    def test_odd_roster_produces_one_pair_more_than_halving_the_roster(self):
        # 9 men => 5 pairs, not 4 pairs plus a leftover man.
        for counter in range(len(self.ODD_ROSTER)):
            pairs = pair_generator.rotated_pairs(self.ODD_ROSTER, counter)
            self.assertEqual(len(pairs), (len(self.ODD_ROSTER) + 1) // 2)

    def test_odd_roster_never_emits_a_lone_man_or_dummy_slot(self):
        # The dummy slot used for the pairing math must never reach the output.
        for counter in range(len(self.ODD_ROSTER)):
            for pair in pair_generator.rotated_pairs(self.ODD_ROSTER, counter):
                self.assertEqual(len(pair), 2)
                self.assertNotIn(None, pair)
                self.assertNotEqual(pair[0], pair[1])

    def test_odd_roster_every_man_is_paired_every_week(self):
        for counter in range(len(self.ODD_ROSTER)):
            paired = set()
            for a, b in pair_generator.rotated_pairs(self.ODD_ROSTER, counter):
                paired.update((a, b))
            self.assertEqual(paired, set(self.ODD_ROSTER))

    def test_odd_roster_doubles_up_exactly_one_man_each_week(self):
        for counter in range(len(self.ODD_ROSTER)):
            counts = {man: 0 for man in self.ODD_ROSTER}
            for a, b in pair_generator.rotated_pairs(self.ODD_ROSTER, counter):
                counts[a] += 1
                counts[b] += 1

            doubled = [man for man, count in counts.items() if count == 2]
            self.assertEqual(len(doubled), 1)
            # Everyone else is in exactly one pair.
            self.assertTrue(all(count in (1, 2) for count in counts.values()))

    def test_odd_roster_doubled_man_gets_two_different_partners(self):
        for counter in range(len(self.ODD_ROSTER)):
            pairs = pair_generator.rotated_pairs(self.ODD_ROSTER, counter)
            counts = {man: 0 for man in self.ODD_ROSTER}
            for a, b in pairs:
                counts[a] += 1
                counts[b] += 1

            doubled = next(man for man, count in counts.items() if count == 2)
            partners = [
                other
                for pair in pairs
                if doubled in pair
                for other in pair
                if other != doubled
            ]
            self.assertEqual(len(partners), 2)
            self.assertEqual(len(set(partners)), 2)

    def test_even_roster_never_doubles_anyone_up(self):
        # The double-up is strictly an odd-roster mechanism.
        men = ["A", "B", "C", "D", "E", "F"]
        for counter in range(len(men) - 1):
            counts = {man: 0 for man in men}
            for a, b in pair_generator.rotated_pairs(men, counter):
                counts[a] += 1
                counts[b] += 1

            self.assertTrue(all(count == 1 for count in counts.values()))


if __name__ == '__main__':
    unittest.main()

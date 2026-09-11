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
        # For odd n the round robin takes n weeks, but the schedule does not
        # repeat until n cycles have run: each cycle starts the roster at a
        # different position so the double-ups and the extra pairings move on
        # to other men instead of falling to the same ones every cycle.
        self.assertNotEqual(
            pair_generator.rotated_pairs(men, len(men)),
            pair_generator.rotated_pairs(men, 0),
        )
        self.assertEqual(
            pair_generator.rotated_pairs(men, len(men) ** 2),
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
        # Holds for the whole run, cycle boundaries included.
        men = [f"Person {number}" for number in range(1, 10)]
        weeks = [
            {frozenset(pair) for pair in pair_generator.rotated_pairs(men, week)}
            for week in range(len(men) ** 2)
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

    A pair needs two men, so an odd roster cannot leave one man over -- a group
    of one is not a pair. Rather than giving that man a bye, the generator pairs
    him a second time with another man from the same week. A name appearing
    twice in a week's output is therefore intended behaviour, not a bug.

    Sharing the double-ups perfectly evenly inside a single cycle is
    impossible, so the schedule runs a different arrangement of the roster each
    cycle and evens out over a full run of n cycles. These tests check the
    guarantees that hold every week and the fairness that holds over the run.

    Real roster names are confidential and must never appear in this repository,
    so these tests use placeholder names.
    """

    ODD_ROSTER = [f"Person {number}" for number in range(1, 10)]

    @staticmethod
    def _doubled_man(pairs):
        counts = {}
        for first, second in pairs:
            counts[first] = counts.get(first, 0) + 1
            counts[second] = counts.get(second, 0) + 1
        doubled = [man for man, count in counts.items() if count == 2]
        return doubled[0] if len(doubled) == 1 else None

    def test_odd_roster_produces_one_pair_more_than_halving_the_roster(self):
        # 9 men => 5 pairs, not 4 pairs plus a leftover man.
        for counter in range(len(self.ODD_ROSTER) ** 2):
            pairs = pair_generator.rotated_pairs(self.ODD_ROSTER, counter)
            self.assertEqual(len(pairs), (len(self.ODD_ROSTER) + 1) // 2)

    def test_odd_roster_never_emits_a_lone_man_or_dummy_slot(self):
        # The dummy slot used for the pairing math must never reach the output.
        for counter in range(len(self.ODD_ROSTER) ** 2):
            for pair in pair_generator.rotated_pairs(self.ODD_ROSTER, counter):
                self.assertEqual(len(pair), 2)
                self.assertNotIn(None, pair)
                self.assertNotEqual(pair[0], pair[1])

    def test_odd_roster_every_man_is_paired_every_week(self):
        for counter in range(len(self.ODD_ROSTER) ** 2):
            paired = set()
            for a, b in pair_generator.rotated_pairs(self.ODD_ROSTER, counter):
                paired.update((a, b))
            self.assertEqual(paired, set(self.ODD_ROSTER))

    def test_odd_roster_doubles_up_exactly_one_man_each_week(self):
        for counter in range(len(self.ODD_ROSTER) ** 2):
            pairs = pair_generator.rotated_pairs(self.ODD_ROSTER, counter)
            self.assertIsNotNone(self._doubled_man(pairs))

    def test_odd_roster_doubled_man_gets_two_different_partners(self):
        for counter in range(len(self.ODD_ROSTER) ** 2):
            pairs = pair_generator.rotated_pairs(self.ODD_ROSTER, counter)
            doubled = self._doubled_man(pairs)
            partners = [
                other
                for pair in pairs
                if doubled in pair
                for other in pair
                if other != doubled
            ]
            self.assertEqual(len(partners), 2)
            self.assertEqual(len(set(partners)), 2)

    def test_no_man_doubles_up_in_consecutive_weeks(self):
        # Doubling up two weeks running is the thing to avoid, so it is a hard
        # guarantee: it holds inside a cycle and across a cycle boundary.
        for roster_size in (5, 7, 9, 11):
            men = [f"Person {number}" for number in range(1, roster_size + 1)]
            previous = None
            for counter in range(roster_size ** 2 + 1):
                doubled = self._doubled_man(pair_generator.rotated_pairs(men, counter))
                self.assertNotEqual(
                    doubled,
                    previous,
                    f"roster of {roster_size}: {doubled} doubles up in weeks "
                    f"{counter - 1} and {counter}",
                )
                previous = doubled

    def test_no_two_men_are_paired_in_consecutive_weeks(self):
        # Likewise for a pairing: the same two men are never put together two
        # weeks running, cycle boundaries included.
        for roster_size in (5, 7, 9, 11):
            men = [f"Person {number}" for number in range(1, roster_size + 1)]
            previous = set()
            for counter in range(roster_size ** 2 + 1):
                pairs = {
                    frozenset(pair)
                    for pair in pair_generator.rotated_pairs(men, counter)
                }
                self.assertFalse(
                    pairs & previous,
                    f"roster of {roster_size}: week {counter} repeats a pairing "
                    f"from week {counter - 1}",
                )
                previous = pairs

    def test_every_man_doubles_up_equally_often_over_a_full_run(self):
        # The point of the rotation: double-up duty is shared equally rather
        # than concentrated on any one man. It cannot come out even within a
        # single cycle, so the guarantee is over the full run of n cycles.
        for roster_size in (5, 7, 9, 11):
            men = [f"Person {number}" for number in range(1, roster_size + 1)]
            doubled_counts = {man: 0 for man in men}

            for counter in range(roster_size ** 2):
                pairs = pair_generator.rotated_pairs(men, counter)
                doubled_counts[self._doubled_man(pairs)] += 1

            self.assertEqual(
                set(doubled_counts.values()),
                {roster_size},
                f"roster of {roster_size} shares double-ups unevenly: {doubled_counts}",
            )

    def test_double_up_is_not_biased_towards_the_first_man_listed(self):
        # Regression test: choosing the extra partner one week at a time made
        # the search settle on whoever was listed first, who then doubled up in
        # most weeks of the cycle.
        men = [f"Person {number}" for number in range(1, 10)]
        first_man = men[0]
        weeks_doubled = sum(
            1
            for counter in range(len(men) ** 2)
            if self._doubled_man(pair_generator.rotated_pairs(men, counter)) == first_man
        )

        self.assertEqual(weeks_doubled, len(men))

    def test_extra_pairing_does_not_single_out_the_same_men_every_cycle(self):
        # A pair that gets the extra pairing is together twice in that cycle.
        # Repeating one cycle forever would favour those men permanently, so
        # the extra pairings have to move on to other men as cycles go by.
        men = [f"Person {number}" for number in range(1, 10)]
        size = len(men)
        extras_by_cycle = []

        for cycle in range(size):
            extras = set()
            for week in range(size):
                pairs = pair_generator.rotated_pairs(men, cycle * size + week)
                doubled = self._doubled_man(pairs)
                seen = set()
                for pair in pairs:
                    if doubled in pair:
                        seen.add(frozenset(pair))
                extras |= seen
            extras_by_cycle.append(extras)

        # No cycle hands the extra pairings to exactly the same men as another.
        for cycle, extras in enumerate(extras_by_cycle):
            for other in range(cycle + 1, size):
                self.assertNotEqual(extras, extras_by_cycle[other])

        # And no single pair collects the extra pairing in every cycle.
        for pair in set().union(*extras_by_cycle):
            cycles_with_pair = sum(1 for e in extras_by_cycle if pair in e)
            self.assertLess(cycles_with_pair, size)

    def test_no_two_men_are_paired_far_more_often_than_any_other_two(self):
        # Over a full run every pair should come up a similar number of times.
        men = [f"Person {number}" for number in range(1, 10)]
        size = len(men)
        togetherness = {}

        for counter in range(size ** 2):
            for pair in pair_generator.rotated_pairs(men, counter):
                key = frozenset(pair)
                togetherness[key] = togetherness.get(key, 0) + 1

        # Every possible pair comes up, and the busiest pair is not a large
        # multiple of the quietest.
        self.assertEqual(len(togetherness), size * (size - 1) // 2)
        self.assertLessEqual(max(togetherness.values()), min(togetherness.values()) * 2)

    def test_double_up_rotation_does_not_depend_on_roster_order(self):
        # Reordering the roster reorders who doubles up when, but every man
        # still takes the duty equally often over a full run.
        men = list(reversed([f"Person {number}" for number in range(1, 10)]))
        doubled_counts = {man: 0 for man in men}

        for counter in range(len(men) ** 2):
            pairs = pair_generator.rotated_pairs(men, counter)
            doubled_counts[self._doubled_man(pairs)] += 1

        self.assertEqual(set(doubled_counts.values()), {len(men)})

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

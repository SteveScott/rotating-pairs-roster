# Rotating Pairs Roster

Generates weekly pairings for a roster of men, rotating each week so that
everyone eventually meets everyone else.

## Roster file

The script reads `roster.txt` from the repository root — one name per line.
Blank lines are ignored.

```
Name One
Name Two
Name Three
```

**`roster.txt` is confidential and is never committed.** It is listed in
`.gitignore`, and real names must not appear anywhere in this repository —
not in source, tests, comments, commit messages, or documentation. Tests and
examples use placeholders (`A`, `B`, `C` … or `Person 1`, `Person 2` …)
for exactly this reason. Keep it that way when adding code.

## Usage

```bash
python3 rotating-pair-generator.py        # uses the current ISO week number
python3 rotating-pair-generator.py 12     # uses an explicit rotation counter
```

The counter selects which round of the rotation to print. It is taken modulo
the cycle length, so counters beyond one full cycle wrap around.

## How the pairing works

Pairings use the **circle method** for round-robin scheduling:

1. Arrange the men in a fixed list of slots.
2. Pair from the outside in — first with last, second with second-last, and so on.
3. Hold slot 0 fixed.
4. Rotate every other slot by one position each round.

Repeating the rotation walks the whole round-robin schedule, so over a full
cycle each man is paired with every other man.

For an **even** roster of `n` men this gives `n / 2` pairs per week and a
cycle length of `n - 1` weeks.

## Odd rosters: nobody sits out

A pair needs two men, so an odd roster cannot simply leave one man over — a
group of one is not a pair.

The usual round-robin answer is to add a dummy slot and let whoever draws it
take a bye that week. **This script does not do that.** Instead the man who
would have taken the bye is paired a second time, with another man from that
same week. So for an odd roster of `n` men:

- every man is in a pair every week — there is no bye and no one-man group,
- exactly one man is in **two** pairs that week,
- that week has `(n + 1) / 2` pairs, not `n / 2` rounded down,
- the cycle length is `n` weeks.

For a 9-man roster that means 5 pairs per week, with one man appearing twice.
A name showing up twice in the output is the intended behaviour, not a bug.

The second partner is chosen so that it does not repeat a pairing from the
previous, current, or next rotation, which keeps consecutive weeks from
producing the same two men together.

### Known characteristic: doubling is not evenly spread

Because the circle method holds slot 0 fixed, the man in the first roster
position draws the double-up far more often than the rest. Over a full
9-week cycle on a 9-man roster, the first-listed man is doubled 6 times
while most men are never doubled at all. Reordering `roster.txt` changes who
absorbs it but not the skew itself. If even distribution matters, the
double-up selection needs to account for how often each man has already been
doubled.

## Tests

```bash
python3 -m unittest test_rotating_pair_generator -v
```

The suite covers even and odd rosters, cycle/modulo behaviour, full-sweep
coverage that every man meets every other man, the odd-roster double-up
rules above, and the error message for a missing `roster.txt`.

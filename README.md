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

### The double-up rotates evenly

Over a full cycle **every man takes the second pair exactly once** — on a
9-man roster, one double-up each across the 9 weeks. That is a guarantee
rather than a tendency, because the extra partners are chosen for the whole
cycle at once as a permutation of the roster, not picked a week at a time.
Picking week by week is what an earlier version did, and it kept settling on
whoever was listed first in `roster.txt`, who then doubled up in 6 weeks out
of 9 while most men never doubled at all.

Reordering `roster.txt` changes *which* week a given man doubles up. It does
not change the even share.

### Why one pairing repeats per cycle

Ideally a double-up pair would also never repeat a pairing from the week
before or after, so the same two men are never together in consecutive weeks.
On an odd roster that cannot be combined with an even rotation.

The reason is structural. In every round, the man paired with the *next*
round's leftover man is the same man throughout the cycle, so he is ruled out
as an extra partner in every round but one. Two men end up competing for that
single round, and by Hall's theorem no assignment can give every man a turn.
Something has to give, and an even rotation is the point of the exercise, so
it is the constraint that holds.

Repeats are therefore minimised rather than forbidden, and the minimum works
out to exactly **one repeated pairing per cycle** at every roster size. The
generator finds that minimum exactly, by solving the choice of extra partners
as a min-cost assignment problem rather than by searching greedily.

## Tests

```bash
python3 -m unittest test_rotating_pair_generator -v
```

The suite covers even and odd rosters, cycle/modulo behaviour, full-sweep
coverage that every man meets every other man, the odd-roster double-up
rules above, and the error message for a missing `roster.txt`.

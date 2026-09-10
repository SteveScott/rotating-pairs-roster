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

The counter selects which week of the schedule to print, counting from week 0.

## How the pairing works

Pairings use the **circle method** for round-robin scheduling:

1. Arrange the men in a fixed list of slots.
2. Pair from the outside in — first with last, second with second-last, and so on.
3. Hold slot 0 fixed.
4. Rotate every other slot by one position each round.

Repeating the rotation walks the whole round-robin schedule, so over one cycle
each man is paired with every other man.

For an **even** roster of `n` men this gives `n / 2` pairs per week, one
partner each, and a cycle of `n - 1` weeks that then repeats.

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
- one cycle of the round robin takes `n` weeks.

For a 9-man roster that means 5 pairs per week, with one man appearing twice.
A name showing up twice in the output is the intended behaviour, not a bug.

## What the schedule guarantees

Two rules hold **every week without exception**, including across the boundary
between one cycle and the next:

- **No man doubles up two weeks running.** Taking the second pair is the extra
  ask of the week, and it never lands on the same man twice in a row.
- **No two men are paired two weeks running.** Whoever you are paired with
  this week, you will not be paired with again next week.

Two more hold **over a full run** (see below for why they cannot hold within a
single cycle):

- **No man doubles up more often than any other.** Over a full run every man
  takes the second pair exactly `n` times.
- **No two men are singled out for extra pairings.** The pairs that get an
  extra meeting change from cycle to cycle rather than being fixed for good.

## Why the schedule runs for `n` cycles, not one

One cycle of `n` weeks covers the round robin, so it is tempting to just repeat
it. That would be unfair in two ways that compound every cycle.

Within a single cycle the double-ups **cannot** be shared out evenly. In every
round, the man paired with the *next* round's leftover man is the same man
throughout, so he can serve as the extra partner in only one round of the
cycle. Two men end up competing for that single round, and by Hall's theorem no
assignment gives every man exactly one turn. The best a single cycle can do is
one man twice, one man never, and everyone else once.

Repeating that same cycle would freeze both unfairnesses in place: the same man
would double up twice every cycle, the same man never, and the same handful of
pairs would get a second meeting every cycle while the rest got one.

So each cycle instead starts the roster at a different position. That moves the
leftover man, the double-ups, and the extra pairings on to different men, and
after `n` cycles every man has taken every position. The schedule repeats every
`n × n` weeks — 81 weeks for a 9-man roster — and over that run:

- every man doubles up exactly `n` times,
- every possible pair comes up, and the busiest pair meets no more than twice
  as often as the quietest.

The order of the cycles is not arbitrary either. A cycle boundary is just
another pair of consecutive weeks, so the cycles are ordered such that no
boundary repeats a pairing or doubles up the same man twice running.

## Tests

```bash
python3 -m unittest test_rotating_pair_generator -v
```

The suite covers even and odd rosters, cycle length and repeat behaviour,
full-sweep coverage that every man meets every other man, all four guarantees
above, and the error message for a missing `roster.txt`.

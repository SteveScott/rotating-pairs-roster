"""Generate the weekly pairings for a roster of men.

Pairs come from the circle method for round-robin scheduling, so over one cycle
every man is paired with every other man. An odd roster gets no bye: the man who
would otherwise sit out is paired a second time that week, because a group of
one is not a pair. One man is therefore in two pairs each week.

The schedule runs for n cycles before repeating, starting the roster at a
different position each cycle. That is what keeps it fair; README.md explains
why a single cycle cannot be. Every week, without exception and including
across the boundary between cycles:

- no man doubles up two weeks running,
- no two men are paired two weeks running.

And over a full run of n cycles:

- every man doubles up exactly n times,
- no two men are singled out for the extra pairings.

The roster itself lives in roster.txt, which is confidential and gitignored.
Real names must not appear in this file, or anywhere else in this repository.
"""

import sys
from datetime import date
from functools import lru_cache
from pathlib import Path


def load_roster(file_path):
	"""Load roster names from a text file (one name per line)."""
	path = Path(file_path)
	if not path.exists():
		raise FileNotFoundError(
			f"Roster file not found: {path}. "
			"Create roster.txt with one name per line."
		)

	with open(path, 'r', encoding='utf-8') as f:
		roster = [line.strip() for line in f if line.strip()]

	if not roster:
		raise ValueError(
			f"Roster file is empty: {path}. "
			"Add at least one name per line."
		)

	return roster


ROSTER_FILE = Path(__file__).with_name('roster.txt')

# Which week of the schedule to print, counting from week 0. Defaults to the
# current ISO week number.
ROTATION_COUNTER = date.today().isocalendar()[1]


def circle_pairs(players, round_index):
	"""Return the regular circle-method pairs and any odd-roster bye."""
	rotated = players[:]
	for _ in range(round_index):
		rotated = [rotated[0]] + [rotated[-1]] + rotated[1:-1]

	pairs = []
	bye_man = None
	total = len(rotated)
	for i in range(total // 2):
		a = rotated[i]
		b = rotated[total - 1 - i]
		if a is None or b is None:
			bye_man = b if a is None else a
			continue
		pairs.append((a, b))
	return pairs, bye_man


def _doubled_man(pairs):
	"""Return the man who appears in two of one round's pairs, if any."""
	counts = {}
	for first, second in pairs:
		counts[first] = counts.get(first, 0) + 1
		counts[second] = counts.get(second, 0) + 1
	for man, count in counts.items():
		if count == 2:
			return man
	return None


def _extra_partners(arrangement, max_double_ups):
	"""Choose every round's extra partner for one cycle of an odd roster.

	The circle method leaves one man out of the regular pairs each round: the
	man drawn against the dummy slot. He is paired a second time with a man who
	already has a partner that round, so nobody sits out, and that extra partner
	is the man who ends up in two pairs.

	These constraints are all hard, and the search reports failure rather than
	bending them:

	- no man is his own partner,
	- an extra pair never repeats a pairing from the round before or after,
	- two rounds running never share the same extra pair,
	- the same man never doubles up two rounds running,
	- no man doubles up more than `max_double_ups` times in the cycle.

	Candidates are tried least-used first, so the double-ups land as evenly as
	the constraints allow. Returns one extra partner per round, or None when no
	assignment satisfies the constraints.
	"""
	size = len(arrangement)
	players = list(arrangement) + [None]
	rounds = [circle_pairs(players, index) for index in range(size)]
	leftovers = [leftover for _, leftover in rounds]
	round_pairs = [{frozenset(pair) for pair in pairs} for pairs, _ in rounds]
	position = {man: index for index, man in enumerate(arrangement)}

	candidates = []
	for index in range(size):
		leftover = leftovers[index]
		candidates.append([
			man
			for man in arrangement
			if man != leftover
			and frozenset((leftover, man)) not in round_pairs[(index - 1) % size]
			and frozenset((leftover, man)) not in round_pairs[(index + 1) % size]
		])

	used = {man: 0 for man in arrangement}
	chosen = [None] * size

	def extend(index):
		if index == size:
			return True

		order = sorted(candidates[index], key=lambda man: (used[man], position[man]))
		for man in order:
			if used[man] >= max_double_ups:
				continue
			if index:
				previous = chosen[index - 1]
				if man == previous:
					continue
				if frozenset((leftovers[index], man)) == frozenset(
					(leftovers[index - 1], previous)
				):
					continue

			used[man] += 1
			chosen[index] = man
			if extend(index + 1):
				return True
			used[man] -= 1
			chosen[index] = None
		return False

	return list(chosen) if extend(0) else None


def _cycle_rounds(arrangement):
	"""Return the pairs for each round of one cycle of an odd roster.

	Sharing the double-ups perfectly evenly within a single cycle is
	impossible. In every round the man paired with the next round's leftover
	man is the same one, so he can serve as an extra partner in only one round
	of the cycle; two men then compete for that round, and by Hall's theorem no
	assignment gives each man exactly one turn. The search therefore starts by
	allowing two double-ups per man, and only loosens that if it has to. The
	remaining unevenness is evened out across cycles by `_odd_schedule`.
	"""
	size = len(arrangement)
	players = list(arrangement) + [None]
	rounds = [circle_pairs(players, index) for index in range(size)]

	for max_double_ups in range(2, size + 1):
		partners = _extra_partners(arrangement, max_double_ups)
		if partners is not None:
			return [
				pairs + [(leftover, partners[index])]
				for index, (pairs, leftover) in enumerate(rounds)
			]

	raise RuntimeError('Unable to schedule the odd-roster double-ups.')


def _seam_safe_order(cycles):
	"""Order the cycles so no cycle boundary repeats a pair or a doubled man.

	Each cycle appears exactly once in the order, so over a full run every man
	takes every position in the rotation. The constraints that hold inside a
	cycle have to hold across its boundary too, which rules out some orderings;
	the rest is a Hamiltonian cycle over the compatible ones.
	"""
	size = len(cycles)
	compatible = [[False] * size for _ in range(size)]
	for first in range(size):
		closing = cycles[first][-1]
		closing_pairs = {frozenset(pair) for pair in closing}
		for second in range(size):
			opening = cycles[second][0]
			if closing_pairs & {frozenset(pair) for pair in opening}:
				continue
			compatible[first][second] = _doubled_man(closing) != _doubled_man(opening)

	order = []
	visited = set()

	def extend(offset):
		order.append(offset)
		visited.add(offset)

		if len(order) == size:
			if compatible[offset][order[0]]:
				return True
		else:
			for candidate in range(size):
				if candidate not in visited and compatible[offset][candidate]:
					if extend(candidate):
						return True

		order.pop()
		visited.discard(offset)
		return False

	if not extend(0):
		raise RuntimeError('Unable to order the cycles without a repeat at a boundary.')
	return order


@lru_cache(maxsize=None)
def _odd_schedule(men):
	"""Return every cycle of an odd roster's schedule, in the order they run.

	One cycle covers the round robin, but running the same cycle over and over
	would hand the same men the extra pairing every time. Each cycle therefore
	starts the roster at a different position, which moves the double-ups and
	the extra pairings on to different men. Over a full run of `n` cycles every
	man doubles up equally often.
	"""
	size = len(men)
	cycles = [_cycle_rounds(men[offset:] + men[:offset]) for offset in range(size)]
	return tuple(cycles[offset] for offset in _seam_safe_order(cycles))


def rotated_pairs(men, counter):
	"""Return the pairs for one week using the circle method.

	How the circle method works:
	1) Arrange players in a fixed list of slots.
	2) Pair from the outside in: first with last, second with second-last, etc.
	3) Keep slot 0 fixed.
	4) Rotate all other slots by one position each round.

	Why this works:
	- Each round creates non-overlapping pairs for that round.
	- Repeating this rotation visits every edge in the round-robin schedule.
	- For an even roster of n men, the cycle is n - 1 weeks long and every man
	  has exactly one partner each week.
	- For an odd roster, a dummy slot stands in for the missing man, and the
	  would-be bye becomes an extra pair so that nobody sits out. One man is
	  therefore in two pairs each week. The cycle is n weeks long, and the
	  schedule repeats every n cycles rather than every cycle, so that the
	  double-ups and the extra pairings do not keep falling to the same men.
	"""
	if len(men) < 2:
		return []

	men_list = list(men)
	size = len(men_list)

	if size % 2 == 0:
		pairs, _ = circle_pairs(men_list, counter % (size - 1))
		return pairs

	schedule = _odd_schedule(tuple(men_list))
	cycle = schedule[(counter // size) % size]
	return cycle[counter % size]


def print_rotation(men, counter):
	pairs = rotated_pairs(men, counter)
	size = len(men)
	print(f"requested counter = {counter}")
	if size % 2 == 0:
		cycle_len = max(1, size - 1)
		print(f"effective rotation (mod {cycle_len}) = {counter % cycle_len}")
	else:
		print(
			f"cycle {(counter // size) % size + 1} of {size}, "
			f"week {counter % size + 1} of {size}"
		)
	for a, b in pairs:
		print(f"{a} + {b}")


if __name__ == '__main__':
	print(f"running script: {__file__}")
	try:
		roster = load_roster(ROSTER_FILE)
	except (FileNotFoundError, ValueError) as exc:
		print('ERROR: Unable to load roster file.')
		print(str(exc))
		print(f'Expected location: {ROSTER_FILE}')
		raise SystemExit(1)

	# Allow the first CLI argument to override the default rotation counter.
	if len(sys.argv) > 1:
		try:
			counter = int(sys.argv[1])
		except ValueError:
			print(f"ERROR: Counter must be an integer, got: {sys.argv[1]}")
			raise SystemExit(2)
	else:
		counter = ROTATION_COUNTER
	print_rotation(roster, counter)

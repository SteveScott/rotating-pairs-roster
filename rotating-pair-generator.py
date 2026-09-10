import sys
from datetime import date
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

# Set this value to rotate pairings. Defaults to the current ISO week number.
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


def _min_cost_assignment(cost):
	"""Give each row a distinct column at the lowest total cost.

	`cost` must be square. Returns a list mapping each row index to the column
	index assigned to it, so the result is always a permutation. This is the
	Hungarian algorithm with potentials, which runs in cubic time.
	"""
	size = len(cost)
	unreached = float('inf')
	row_potential = [0] * (size + 1)
	col_potential = [0] * (size + 1)
	col_owner = [0] * (size + 1)
	came_from = [0] * (size + 1)

	for row in range(1, size + 1):
		col_owner[0] = row
		col = 0
		cheapest = [unreached] * (size + 1)
		used = [False] * (size + 1)

		while True:
			used[col] = True
			owner = col_owner[col]
			delta = unreached
			next_col = -1

			for candidate in range(1, size + 1):
				if used[candidate]:
					continue
				reduced = (
					cost[owner - 1][candidate - 1]
					- row_potential[owner]
					- col_potential[candidate]
				)
				if reduced < cheapest[candidate]:
					cheapest[candidate] = reduced
					came_from[candidate] = col
				if cheapest[candidate] < delta:
					delta = cheapest[candidate]
					next_col = candidate

			for candidate in range(size + 1):
				if used[candidate]:
					row_potential[col_owner[candidate]] += delta
					col_potential[candidate] -= delta
				else:
					cheapest[candidate] -= delta

			col = next_col
			if col_owner[col] == 0:
				break

		while col:
			previous = came_from[col]
			col_owner[col] = col_owner[previous]
			col = previous

	assignment = [0] * size
	for col in range(1, size + 1):
		if col_owner[col]:
			assignment[col_owner[col] - 1] = col - 1
	return assignment


def odd_double_up_pairs(men, players):
	"""Pick each round's extra pair so that double-ups rotate evenly.

	The circle method leaves exactly one man out of the regular pairs each
	round: the man drawn against the dummy slot. He is paired a second time
	with a man who already has a partner that round, so nobody sits out. That
	extra partner is the man who ends up in two pairs for the week.

	Who doubles up is a fairness question, so it is settled for the whole cycle
	at once instead of one round at a time. The extra partners are chosen as a
	permutation of the roster, which gives every man exactly one double-up per
	cycle. Choosing round by round instead lets the search settle on whoever
	sits earliest in the roster, which made the first-listed man double up in
	most weeks of the cycle.

	Repeating a pairing from a neighbouring week is penalised but cannot always
	be avoided. In every round the man paired with the next round's leftover
	man is the same one, so he is blocked in all but one round, and demanding
	both an even rotation and no neighbouring repeat is infeasible. The even
	rotation is the guarantee; neighbouring repeats are merely minimised, which
	works out to one per cycle.
	"""
	cycle_len = len(players) - 1
	regular_rounds = [circle_pairs(players, index) for index in range(cycle_len)]
	regular_pairs = [
		{frozenset(pair) for pair in pairs} for pairs, _ in regular_rounds
	]

	# No man may partner himself, so that choice is priced beyond any total the
	# neighbouring-repeat penalties can reach.
	forbidden = 100 * cycle_len
	cost = []
	for index, (_, bye_man) in enumerate(regular_rounds):
		neighbours = ((index - 1) % cycle_len, (index + 1) % cycle_len)
		next_bye_man = regular_rounds[(index + 1) % cycle_len][1]
		row = []
		for man in men:
			if man == bye_man:
				row.append(forbidden)
				continue
			pair = frozenset((bye_man, man))
			penalty = sum(1 for other in neighbours if pair in regular_pairs[other])
			# Handing this round's leftover man to the next round's leftover man is
			# the one way two consecutive rounds can share the same extra pair.
			if man == next_bye_man:
				penalty += 1
			row.append(penalty)
		cost.append(row)

	assignment = _min_cost_assignment(cost)
	if any(cost[index][assignment[index]] >= forbidden for index in range(cycle_len)):
		raise RuntimeError('Unable to build odd-roster pairings without a self-pair.')

	return [
		(regular_rounds[index][1], men[assignment[index]])
		for index in range(cycle_len)
	]


def rotated_pairs(men, counter):
	"""Return round-robin pairs for one rotation using the circle method.

	How the circle method works:
	1) Arrange players in a fixed list of slots.
	2) Pair from the outside in: first with last, second with second-last, etc.
	3) Keep slot 0 fixed.
	4) Rotate all other slots by one position each round.

	Why this works:
	- Each round creates non-overlapping pairs for that round.
	- Repeating this rotation visits every edge in the round-robin schedule.
	- For even n players, cycle length is n - 1 rounds.
	- For odd n players, add a dummy slot (None), then convert the would-be bye
	  into an extra pair so nobody sits out. The extra partner is chosen to avoid
	  a pair from either the current or previous rotation.

	`counter` selects the round number modulo the cycle length.
	"""
	if len(men) < 2:
		return []

	men_list = list(men)
	players = men_list[:]
	# For odd roster sizes, add a dummy player so pairing math stays symmetric.
	is_odd = len(players) % 2 == 1
	if is_odd:
		players.append(None)

	total = len(players)
	cycle_len = total - 1
	round_index = counter % cycle_len

	pairs, bye_man = circle_pairs(players, round_index)

	if is_odd and bye_man is not None:
		double_up_pair = odd_double_up_pairs(men_list, players)[round_index]
		pairs.append(tuple(double_up_pair))

	return pairs


def print_rotation(men, counter):
	pairs = rotated_pairs(men, counter)
	total = len(men) if len(men) % 2 == 0 else len(men) + 1
	cycle_len = max(1, total - 1)
	effective = counter % cycle_len
	print(f"requested counter = {counter}")
	print(f"effective rotation (mod {cycle_len}) = {effective}")
	for idx, (a, b) in enumerate(pairs, start=1):
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

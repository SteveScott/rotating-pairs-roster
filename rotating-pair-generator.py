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


def odd_double_up_pairs(men, players):
	"""Choose one extra pair per odd-roster round without adjacent repeats."""
	cycle_len = len(players) - 1
	regular_rounds = [circle_pairs(players, index) for index in range(cycle_len)]
	candidates_by_round = []
	for index, (pairs, bye_man) in enumerate(regular_rounds):
		blocked_pairs = {
			frozenset(pair)
			for neighbor in ((index - 1) % cycle_len, index, (index + 1) % cycle_len)
			for pair in regular_rounds[neighbor][0]
		}
		candidates_by_round.append([
			(bye_man, man)
			for man in men
			if man != bye_man and frozenset((bye_man, man)) not in blocked_pairs
		])

	def choose(round_index, chosen):
		if round_index == cycle_len:
			return chosen if chosen[-1] != chosen[0] else None
		for pair in candidates_by_round[round_index]:
			if not chosen or pair != chosen[-1]:
				result = choose(round_index + 1, chosen + [pair])
				if result is not None:
					return result
		return None

	chosen = choose(0, [])
	if chosen is None:
		raise RuntimeError('Unable to build non-repeating odd-roster pairings.')
	return chosen


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

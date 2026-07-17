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
	  into an extra pair so nobody sits out. This creates one rotating double-up
	  player each round.

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

	rotated = players[:]
	for _ in range(round_index):
		# Circle rotation step: keep slot 0 fixed and rotate the remaining ring.
		rotated = [rotated[0]] + [rotated[-1]] + rotated[1:-1]

	pairs = []
	bye_man = None
	half = total // 2
	for i in range(half):
		a = rotated[i]
		b = rotated[total - 1 - i]
		# For odd rosters, track the would-be bye so we can give him a real pair.
		if a is None or b is None:
			bye_man = b if a is None else a
			continue
		pairs.append((a, b))

	if is_odd and bye_man is not None:
		# Choose the next roster member after the bye; as bye rotates each round,
		# the double-up role also rotates through everyone.
		bye_idx = men_list.index(bye_man)
		double_up = men_list[(bye_idx + 1) % len(men_list)]
		pairs.append((bye_man, double_up))

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
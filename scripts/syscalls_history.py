#!/usr/bin/env python3
#
# Diff and print added/removed/renamed syscalls between different kernel
# versions of the same arch/bits/abi combination. Input files are JSON tables
# generated by Systrack.
#
# Usage: ./syscalls_history.py table1.json table2.json ...
#

import json
import sys

from glob import glob
from operator import itemgetter
from os import isatty
from typing import List, Tuple

def tag_to_tuple(tag: str) -> Tuple[int,...]:
	if tag == 'latest':
		return (float('inf'),)

	# v5.11 -> (5, 11)
	assert tag[0] == 'v'
	return tuple(map(int, tag[1:].split('.')))

def arch_bits_abi(table: dict) -> str:
	return table['kernel']['architecture']['name'] \
		+ '/' + str(table['kernel']['architecture']['bits']) \
		+ '/' + table['kernel']['abi']['name']

def main(argv: List[str]):
	if len(argv) < 3:
		sys.exit(f'Usage: {argv[0]} table1.json table2.json ...')

	if isatty(sys.stdout.fileno()):
		RED    = '\033[91m'
		GREEN  = '\033[92m'
		BLUE   = '\033[94m'
		RESET  = '\033[0m'
	else:
		GREEN = RED = BLUE = RESET = ''

	PLUS   = GREEN + '+'
	MINUS  = RED + '-'
	RENAME = BLUE + 'R'

	tables = []

	for fnames in map(glob, argv[1:]):
		for fname in fnames:
			with open(fname) as f:
				tables.append(json.load(f))

	tables.sort(key=lambda t: tag_to_tuple(t['kernel']['version']))

	tags = set(map(lambda t: t['kernel']['version'], tables))
	if len(tags) != len(tables):
		sys.exit('Multiple tables for the same kernel version!')

	arch = prev_arch = syscalls = prev_syscalls = None

	for table in tables:
		prev_arch = arch
		prev_syscalls = syscalls

		arch = arch_bits_abi(table)
		if prev_arch is not None and arch != prev_arch:
			sys.exit(f'Incompatible architectures: {prev_arch} and {arch}.\n'
				'Provided tables should all be for the same arch/bits/abi '
				'combination!')

		syscalls = dict(map(itemgetter('number', 'name'), table['syscalls'])).items()
		tag = table['kernel']['version']
		print(f'{tag.ljust(5)}:', len(syscalls), 'syscalls', end='')

		if prev_syscalls is None:
			print()
			continue

		added   = syscalls - prev_syscalls
		removed = prev_syscalls - syscalls

		if not added and not removed:
			print()
			continue

		n_added   = len(added)
		n_removed = len(removed)
		n_renamed = 0
		diff      = {}

		for num, name in removed:
			diff[num] = (MINUS, name)

		for num, name in added:
			if num in diff:
				n_renamed += 1
				n_removed -= 1
				n_added   -= 1
				diff[num] = (RENAME, f'{diff[num][1]} -> {name}')
			else:
				diff[num] = (PLUS, name)

		print(' (', end='')
		if n_added: print(f'{PLUS}{n_added}{RESET}', end='')
		if n_removed: print(('/' if n_added else '') + f'{MINUS}{n_removed}{RESET}', end='')
		if n_renamed: print((', ' if n_added or n_removed else '') + f'{BLUE}{n_renamed} renamed{RESET}', end='')
		print(')')

		for num, (op, name) in sorted(diff.items()):
			print(f'       {op} {num} ({num:#x}) {name}{RESET}')

if __name__ == '__main__':
	main(sys.argv)
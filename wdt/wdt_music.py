"""BGM id lookup in KH1-DOCUMENTATION's music.csv."""
import csv
import os
from pathlib import Path


MUSIC_CSV_RELATIVE_PATH = Path('data') / 'sound' / 'music.csv'

MISSING_TRACK_LABEL = 'NOT IN music.csv'


def find_music_csv():
    env_path = os.environ.get('KH1_MUSIC_CSV')
    if env_path and Path(env_path).is_file():
        return Path(env_path)
    folder_holding_this_repo = Path(__file__).resolve().parents[2]
    for base in (folder_holding_this_repo, Path.cwd(), Path.cwd().parent):
        candidate = base / 'KH1-DOCUMENTATION' / MUSIC_CSV_RELATIVE_PATH
        if candidate.is_file():
            return candidate
    return None


def load_music(path):
    music = {}
    with open(path, encoding='utf-8-sig', newline='') as csv_file:
        for row in csv.DictReader(csv_file):
            try:
                music[int(row['Music ID'])] = row
            except (KeyError, TypeError, ValueError):
                continue
    return music


def music_label(music, music_id):
    if music_id == 0:
        return 'none'
    if not music:
        return ''
    row = music.get(music_id)
    if row is None:
        return MISSING_TRACK_LABEL
    name = row.get('Name')
    if not name:
        name = '?'
    if name == 'N/A':
        return 'empty stub (N/A)'
    return name


def music_detail(music, music_id):
    if not music:
        return ''
    row = music.get(music_id)
    if not row:
        return ''
    parts = [f'music{music_id:03d}.win32.scd']
    if row.get('Duration (s)'):
        parts.append(f'{float(row["Duration (s)"]):.1f} s')
    if row.get('Loops') == 'Yes' and row.get('Loop Start (s)'):
        parts.append(f'loops from {float(row["Loop Start (s)"]):.1f} s')
    elif row.get('Loops') == 'No':
        parts.append('no loop')
    if row.get('Codec', '').startswith('None'):
        parts.append(row['Codec'])
    return ', '.join(parts)

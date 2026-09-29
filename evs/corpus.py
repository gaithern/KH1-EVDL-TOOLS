"""Load every vanilla KGR stream from the game data into a deduplicated cache."""
import hashlib
import os
import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import evdl_tool as et

GAME_DATA = Path(os.environ.get('KH1_GAME_DATA', 'C:/OpenKH/OpenKHEGS/data/kh1'))
CACHE = Path(__file__).parent / 'corpus.pkl'


def find_kgrs_fast(data: bytes) -> list:
    positions = []
    p = data.find(b'KGR\0')
    while p != -1:
        positions.append(p)
        p = data.find(b'KGR\0', p + 1)
    out = []
    for i, p in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(data)
        s = et.trim_stream(data, p + 13, end - (p + 13))
        if not s:
            continue
        n = min(len(s) // 4, 200)
        if sum(1 for j in range(n) if s[j * 4 + 3] in et.VALID_OPS) < n * 0.8:
            continue
        out.append({'kgr_offset': p, 'stream': bytes(s)})
    return out


def load_file(path: Path) -> list:
    data = path.read_bytes()
    if path.suffix.lower() == '.ard':
        try:
            return [{'kgr_offset': k['kgr_offset'], 'ard_section': k['ard_section'], 'stream': bytes(k['stream'])}
                    for k in et.parse_ard(data)]
        except Exception:
            pass
    return find_kgrs_fast(data)


def build():
    files = [p for p in GAME_DATA.rglob('*') if p.suffix.lower() in ('.ard', '.ev', '.evdl')]
    seen = {}
    for i, f in enumerate(files):
        try:
            kgrs = load_file(f)
        except Exception as e:
            print(f'skip {f}: {e}', file=sys.stderr)
            continue
        for k in kgrs:
            h = hashlib.sha1(k['stream']).hexdigest()
            if h not in seen:
                seen[h] = {'src': str(f.relative_to(GAME_DATA)), 'kgr_offset': k['kgr_offset'], 'stream': k['stream']}
        if i % 500 == 0:
            print(f'{i}/{len(files)} files, {len(seen)} unique streams', file=sys.stderr)
    streams = list(seen.values())
    CACHE.write_bytes(pickle.dumps(streams))
    print(f'{len(files)} files -> {len(streams)} unique KGR streams')
    return streams


def load():
    if CACHE.exists():
        return pickle.loads(CACHE.read_bytes())
    return build()


def decode(stream: bytes) -> list:
    """[(opcode, operand24)] for a stream."""
    return [(stream[i + 3], stream[i] | (stream[i + 1] << 8) | (stream[i + 2] << 16))
            for i in range(0, len(stream) - 3, 4)]


if __name__ == '__main__':
    build()

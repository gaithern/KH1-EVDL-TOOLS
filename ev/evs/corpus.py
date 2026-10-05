"""Load every vanilla KGR stream from the game data into a deduplicated cache."""
import hashlib
import os
import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import evdl_format

GAME_DATA = Path(os.environ.get('KH1_GAME_DATA', 'C:/OpenKH/OpenKHEGS/data/kh1'))
CACHE = Path(__file__).parent / 'corpus.pkl'
SCRIPT_SUFFIXES = ('.ard', '.ev', '.evdl')
INSTRUCTION_SIZE = 4
OPCODE_BYTE = 3
OPCODE_SAMPLE_LIMIT = 200
MIN_VALID_OPCODE_FRACTION = 0.8
PROGRESS_EVERY = 500


def kgr_positions(data: bytes) -> list:
    positions = []
    position = data.find(evdl_format.KGR_MAGIC)
    while position != -1:
        positions.append(position)
        position = data.find(evdl_format.KGR_MAGIC, position + 1)
    return positions


def looks_like_code(stream) -> bool:
    sample_size = min(len(stream) // INSTRUCTION_SIZE, OPCODE_SAMPLE_LIMIT)
    valid_count = 0
    for index in range(sample_size):
        if stream[index * INSTRUCTION_SIZE + OPCODE_BYTE] in evdl_format.VALID_OPS:
            valid_count += 1
    return valid_count >= sample_size * MIN_VALID_OPCODE_FRACTION


def find_kgrs_fast(data: bytes) -> list:
    positions = kgr_positions(data)
    kgrs = []
    for index, kgr_offset in enumerate(positions):
        if index + 1 < len(positions):
            end = positions[index + 1]
        else:
            end = len(data)
        stream_start = kgr_offset + evdl_format.KGR_HEADER_SIZE
        stream = evdl_format.trim_stream(data, stream_start, end - stream_start)
        if not stream or not looks_like_code(stream):
            continue
        kgrs.append({'kgr_offset': kgr_offset, 'stream': bytes(stream)})
    return kgrs


def load_ard_kgrs(data: bytes) -> list:
    kgrs = []
    for kgr in evdl_format.parse_ard(data):
        kgrs.append({'kgr_offset': kgr['kgr_offset'], 'ard_section': kgr['ard_section'], 'stream': bytes(kgr['stream'])})
    return kgrs


def load_file(path: Path) -> list:
    data = path.read_bytes()
    if path.suffix.lower() == '.ard':
        try:
            return load_ard_kgrs(data)
        except Exception:
            pass
    return find_kgrs_fast(data)


def build():
    files = [path for path in GAME_DATA.rglob('*') if path.suffix.lower() in SCRIPT_SUFFIXES]
    unique_streams = {}
    for file_index, path in enumerate(files):
        try:
            kgrs = load_file(path)
        except Exception as error:
            print(f'skip {path}: {error}', file=sys.stderr)
            continue
        for kgr in kgrs:
            digest = hashlib.sha1(kgr['stream']).hexdigest()
            if digest not in unique_streams:
                unique_streams[digest] = {'src': str(path.relative_to(GAME_DATA)), 'kgr_offset': kgr['kgr_offset'],
                                          'stream': kgr['stream']}
        if file_index % PROGRESS_EVERY == 0:
            print(f'{file_index}/{len(files)} files, {len(unique_streams)} unique streams', file=sys.stderr)
    streams = list(unique_streams.values())
    CACHE.write_bytes(pickle.dumps(streams))
    print(f'{len(files)} files -> {len(streams)} unique KGR streams')
    return streams


def load():
    if CACHE.exists():
        return pickle.loads(CACHE.read_bytes())
    return build()


def decode(stream: bytes) -> list:
    instructions = []
    for offset in range(0, len(stream) - 3, INSTRUCTION_SIZE):
        operand = stream[offset] | (stream[offset + 1] << 8) | (stream[offset + 2] << 16)
        instructions.append((stream[offset + OPCODE_BYTE], operand))
    return instructions


if __name__ == '__main__':
    build()

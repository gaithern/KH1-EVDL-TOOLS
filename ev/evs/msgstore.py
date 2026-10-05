"""Message tables for compiling EVS string literals: a literal compiles to its index in the set's
.binl, reusing an existing string or appending a new one to every language the script owns."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import binl_tool
from entities import room_and_set, set_binl_name

LANGS = ('UK', 'US', 'FR', 'GR', 'IT', 'SP', 'JP')
DEFAULT_PRIMARY_LANGUAGE = 'UK'
LANGUAGE_PREFIX_RE = re.compile(r'^([A-Z]{2})_')


class MessageStore:
    def __init__(self, sources: dict, targets: dict = None, primary: str = None):
        self.files = {}
        for language, path in sources.items():
            self.files[language] = binl_tool.BinlFile.load(str(path))
        if targets:
            self.targets = targets
        else:
            self.targets = dict(sources)
        if primary in self.files:
            self.primary = primary
        else:
            self.primary = next(iter(self.files))
        self.texts = self.files[self.primary].texts()
        self.dirty = set()

    def get(self, index, default=None):
        if 0 <= index < len(self.texts):
            return self.texts[index]
        return default

    def check_tables_match(self, text):
        counts = {}
        for language, binl in self.files.items():
            counts[language] = len(binl.strings)
        if len(set(counts.values())) != 1:
            raise ValueError(f'cannot append {text!r}: the language tables differ in length {counts}')

    def resolve(self, text: str) -> int:
        if text in self.texts:
            return self.texts.index(text)
        self.check_tables_match(text)
        encoded = binl_tool.encode_string(text)
        new_index = None
        for language, binl in self.files.items():
            appended_index = binl.append(encoded)
            if new_index is not None and appended_index != new_index:
                raise ValueError('language tables went out of step')
            new_index = appended_index
            self.dirty.add(language)
        self.texts.append(text)
        return new_index

    def save(self):
        for language in sorted(self.dirty):
            target = Path(self.targets[language])
            target.parent.mkdir(parents=True, exist_ok=True)
            self.files[language].save(str(target))
        saved = sorted(self.dirty)
        self.dirty.clear()
        return saved


def first_existing(directories, name):
    for directory in directories:
        candidate = Path(directory) / name
        if candidate.is_file():
            return candidate
    return None


def store_for(script: Path, source_dirs, target_dir: Path = None):
    script = Path(script)
    room_set = room_and_set(script)
    if not room_set:
        return None
    room, set_number = room_set
    prefix_match = LANGUAGE_PREFIX_RE.match(script.name)
    if prefix_match:
        languages = (prefix_match.group(1),)
        primary = prefix_match.group(1)
    else:
        languages = LANGS
        primary = DEFAULT_PRIMARY_LANGUAGE
    sources, targets = {}, {}
    for language in languages:
        name = set_binl_name(language, room, set_number)
        found = first_existing(source_dirs, name)
        if not found:
            continue
        sources[language] = found
        if target_dir:
            targets[language] = Path(target_dir) / name
        else:
            targets[language] = found
    if not sources:
        return None
    return MessageStore(sources, targets, primary=primary)

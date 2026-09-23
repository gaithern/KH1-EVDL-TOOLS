"""Message tables for compiling EVS string literals.

`Display_message(1, "text")` compiles to the index of "text" in the set's .binl: an existing
string is reused (exact text match, first index), a new one is appended. Appending never moves
existing strings, so indexes other scripts or the engine rely on stay valid.

A script with a language prefix (UK_di01a.ev) owns only that language's .binl. An unprefixed
script (ew33c.ev) is shared by every language, so a new string is appended to all of them at
the same index; the language copies must hold the same number of strings.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import binl_tool
from entities import BINL_SET_BASE, room_and_set

LANGS = ('UK', 'US', 'FR', 'GR', 'IT', 'SP', 'JP')


class MessageStore:
    def __init__(self, sources: dict, targets: dict = None, primary: str = None):
        """sources: {lang: .binl to read}; targets: {lang: where to save} (default: in place)."""
        self.files = {lang: binl_tool.BinlFile.load(str(p)) for lang, p in sources.items()}
        self.targets = targets or dict(sources)
        self.primary = primary if primary in self.files else next(iter(self.files))
        self.texts = self.files[self.primary].texts()
        self.dirty = set()

    # read access, used to check messages[N]="..." against the table
    def get(self, idx, default=None):
        return self.texts[idx] if 0 <= idx < len(self.texts) else default

    def resolve(self, text: str) -> int:
        """Index of text, appending it to every language's table if it is new."""
        if text in self.texts:
            return self.texts.index(text)
        counts = {lang: len(f.strings) for lang, f in self.files.items()}
        if len(set(counts.values())) != 1:
            raise ValueError(f'cannot append {text!r}: the language tables differ in length {counts}')
        raw = binl_tool.encode_string(text)
        idx = None
        for lang, f in self.files.items():
            i = f.append(raw)
            if idx is not None and i != idx:
                raise ValueError('language tables went out of step')
            idx = i
            self.dirty.add(lang)
        self.texts.append(text)
        return idx

    def save(self):
        for lang in sorted(self.dirty):
            target = Path(self.targets[lang])
            target.parent.mkdir(parents=True, exist_ok=True)
            self.files[lang].save(str(target))
        saved = sorted(self.dirty)
        self.dirty.clear()
        return saved


def store_for(script: Path, source_dirs, target_dir: Path = None):
    """MessageStore for a script's set. source_dirs are searched in order for each .binl
    (e.g. the mod build folder first, then the game's folder); target_dir is where changed
    .binl files are written (default: next to where each was read)."""
    script = Path(script)
    rs = room_and_set(script)
    if not rs:
        return None
    room, set_no = rs
    m = re.match(r'^([A-Z]{2})_', script.name)
    langs = (m.group(1),) if m else LANGS
    sources, targets = {}, {}
    for lang in langs:
        name = f'{lang}_{room}_ard{BINL_SET_BASE + set_no:x}.binl'
        found = next((Path(d) / name for d in source_dirs if (Path(d) / name).is_file()), None)
        if found:
            sources[lang] = found
            targets[lang] = (Path(target_dir) / name) if target_dir else found
    if not sources:
        return None
    return MessageStore(sources, targets, primary=m.group(1) if m else 'UK')

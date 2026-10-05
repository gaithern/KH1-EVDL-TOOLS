"""Decompile and recompile every corpus stream; report exact-match rate and script coverage."""
from collections import Counter
from corpus import load, GAME_DATA
import entities
import lang

MAX_SHOWN_MISMATCHES = 5
MAX_SHOWN_ERRORS = 8
ERROR_TEXT_LIMIT = 80


def round_trip(stream_record, stats):
    source = GAME_DATA / stream_record['src']
    messages = entities.messages_for(source)
    text = lang.decompile(stream_record['stream'], stats, entities.entities_for(source), entities.world_prefix(source),
                          messages)
    return text, lang.compile_text(text, messages)


def report(streams):
    stats = {}
    messages_shown = 0
    exact = 0
    failed = 0
    errors = Counter()
    mismatched_sources = []
    for stream_record in streams:
        try:
            text, recompiled = round_trip(stream_record, stats)
        except Exception as error:
            errors[f'{type(error).__name__}: {error}'[:ERROR_TEXT_LIMIT]] += 1
            failed += 1
            continue
        messages_shown += text.count('messages[')
        if recompiled == stream_record['stream']:
            exact += 1
        else:
            failed += 1
            if len(mismatched_sources) < MAX_SHOWN_MISMATCHES:
                mismatched_sources.append(stream_record['src'])
    print(f'streams round-tripped exactly: {exact}/{exact + failed}')
    print(f"threads as EVS: {stats.get('ok', 0)}, kept as asm: {stats.get('asm', 0)}, raw tails: {stats.get('raw', 0)}")
    print('asm fallback reasons:', stats.get('fail'))
    print('errors:', errors.most_common(MAX_SHOWN_ERRORS))
    print('mismatches:', mismatched_sources)
    print('message texts shown:', messages_shown)


report(load())

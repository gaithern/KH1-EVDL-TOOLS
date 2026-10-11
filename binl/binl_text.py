import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'ev'))
from evdl_format import KH1_CHAR_MAP

END_OF_TIMED_STRING = 0x00
END_OF_DIALOGUE_STRING = 0x04
SPACE = 0x01
LINE_BREAK = 0x02
FIRST_CONTROL_CODE = 0x03
LAST_CONTROL_CODE = 0x1F
LINE_BREAK_TOKEN = '{lf}'
HEX_DIGITS = '0123456789abcdefABCDEF'


def is_control_code(byte):
    return FIRST_CONTROL_CODE <= byte <= LAST_CONTROL_CODE


def control_code_argument_count(code, first_argument):
    if code == 0x05 or code == 0x06 or code == 0x07:
        return 2
    if code == 0x0B or code == 0x0D:
        return 3
    if code == 0x0A:
        if first_argument != 0:
            return 1
        return 3
    if 0x09 <= code <= LAST_CONTROL_CODE:
        return 1
    return 0


def byte_after(data, position):
    if position + 1 < len(data):
        return data[position + 1]
    return 0


def is_hex_digits(text):
    if text == '':
        return False
    for character in text:
        if character not in HEX_DIGITS:
            return False
    return True


def two_digit_hex(byte):
    return '%02X' % byte


def plain_hex_token(byte):
    return '{0x' + two_digit_hex(byte) + '}'


def is_plain_hex_token(text):
    if len(text) != 6:
        return False
    if not text.startswith('{0x'):
        return False
    if not text.endswith('}'):
        return False
    return is_hex_digits(text[3:5])


def control_code_token(code, arguments, argument_count):
    if argument_count == 0:
        return plain_hex_token(code)
    argument_texts = []
    for argument in arguments:
        argument_texts.append(two_digit_hex(argument))
    return '{0x' + two_digit_hex(code) + ' ' + ' '.join(argument_texts) + '}'


def glyph_for_byte(byte):
    if byte in KH1_CHAR_MAP:
        return KH1_CHAR_MAP[byte]
    return plain_hex_token(byte)


def decode_text(raw):
    text = ''
    position = 0
    while position < len(raw):
        byte = raw[position]
        if is_control_code(byte):
            argument_count = control_code_argument_count(byte, byte_after(raw, position))
            arguments = raw[position + 1:position + 1 + argument_count]
            text = text + control_code_token(byte, arguments, argument_count)
            position = position + 1 + argument_count
        elif byte == LINE_BREAK:
            text = text + LINE_BREAK_TOKEN
            position = position + 1
        else:
            text = text + glyph_for_byte(byte)
            position = position + 1
    return text


def build_glyph_to_byte():
    glyph_to_byte = {}
    for byte in KH1_CHAR_MAP:
        glyph = KH1_CHAR_MAP[byte]
        if glyph == '':
            continue
        if is_plain_hex_token(glyph):
            continue
        if glyph in glyph_to_byte:
            continue
        glyph_to_byte[glyph] = byte
    glyph_to_byte[LINE_BREAK_TOKEN] = LINE_BREAK
    glyph_to_byte[' '] = SPACE
    return glyph_to_byte


def named_tokens_longest_first(glyph_to_byte):
    named_tokens = []
    for glyph in glyph_to_byte:
        if glyph.startswith('{'):
            named_tokens.append(glyph)
    return sorted(named_tokens, key=len, reverse=True)


GLYPH_TO_BYTE = build_glyph_to_byte()
NAMED_TOKENS = named_tokens_longest_first(GLYPH_TO_BYTE)


def read_hex_token(text, position):
    closing_brace = text.find('}', position)
    if closing_brace == -1:
        return None
    inside = text[position + 1:closing_brace]
    if not inside.startswith('0x'):
        return None
    code_text = inside[2:4]
    if len(code_text) != 2 or not is_hex_digits(code_text):
        return None
    rest = inside[4:]
    if rest != '' and not rest[0].isspace():
        return None
    numbers = [int(code_text, 16)]
    for argument_text in rest.split():
        if len(argument_text) != 2 or not is_hex_digits(argument_text):
            return None
        numbers.append(int(argument_text, 16))
    token_length = closing_brace + 1 - position
    return numbers, token_length


def check_control_code_arguments(numbers, position):
    code = numbers[0]
    arguments = numbers[1:]
    if not is_control_code(code):
        return
    if code == END_OF_DIALOGUE_STRING:
        return
    first_argument = 0
    if len(arguments) > 0:
        first_argument = arguments[0]
    needed = control_code_argument_count(code, first_argument)
    if len(arguments) != needed:
        raise ValueError(
            'control code {0x%02X} takes %d argument byte(s), got %d '
            '(position %d). Write it as one token, e.g. {0x07 0C 00}.'
            % (code, needed, len(arguments), position))


def unknown_token_error(text, position):
    closing_brace = text.find('}', position)
    if closing_brace >= 0:
        shown_end = closing_brace + 1
    else:
        shown_end = position + 8
    return ValueError('Unknown token %r at position %d' % (text[position:shown_end], position))


def read_named_token(text, position):
    for name in NAMED_TOKENS:
        if text.startswith(name, position):
            return GLYPH_TO_BYTE[name], len(name)
    raise unknown_token_error(text, position)


def byte_for_character(character, position):
    if character == '\n':
        return LINE_BREAK
    if character in GLYPH_TO_BYTE:
        return GLYPH_TO_BYTE[character]
    raise ValueError('Character %r (U+%04X) has no KHSCII mapping (position %d)'
                     % (character, ord(character), position))


def encode_text(text):
    encoded = bytearray()
    position = 0
    while position < len(text):
        character = text[position]
        if character != '{':
            encoded.append(byte_for_character(character, position))
            position = position + 1
            continue
        hex_token = read_hex_token(text, position)
        if hex_token is not None:
            numbers, token_length = hex_token
            check_control_code_arguments(numbers, position)
            encoded.extend(numbers)
            position = position + token_length
        else:
            byte, token_length = read_named_token(text, position)
            encoded.append(byte)
            position = position + token_length
    return bytes(encoded)

from binl_text import END_OF_DIALOGUE_STRING, END_OF_TIMED_STRING
from binl_text import byte_after, control_code_argument_count, decode_text, is_control_code

MAGIC_START = b'EvMsg'
MAGIC_LENGTH = 7
LANGUAGE_START = 5
COUNT_OFFSET = 7
COUNT_SIZE = 4
HEADER_LENGTH = 11
MAX_STRING_COUNT = 100000
PADDING_BYTE = 0xCD
PADDING_ALIGNMENT = 16


class BinlFile:
    def __init__(self, magic, strings, endings, path=None, original_size=0):
        self.magic = magic
        self.strings = strings
        self.endings = endings
        self.path = path
        self.original_size = original_size

    def language(self):
        return self.magic[LANGUAGE_START:MAGIC_LENGTH].decode('ascii', 'replace')

    def texts(self):
        texts = []
        for string in self.strings:
            texts.append(decode_text(string))
        return texts

    def append(self, raw, ending=END_OF_DIALOGUE_STRING):
        self.strings.append(raw)
        self.endings.append(ending)
        return len(self.strings) - 1

    def body_length(self):
        length = HEADER_LENGTH
        for string in self.strings:
            length = length + len(string) + 1
        return length

    def to_bytes(self):
        output = bytearray(self.magic)
        output.extend(len(self.strings).to_bytes(COUNT_SIZE, 'little'))
        for index in range(len(self.strings)):
            output.extend(self.strings[index])
            output.append(self.endings[index])
        target_size = max(self.original_size, len(output))
        while len(output) < target_size or len(output) % PADDING_ALIGNMENT != 0:
            output.append(PADDING_BYTE)
        return bytes(output)

    def save(self, path=None):
        if not path:
            path = self.path
        with open(path, 'wb') as file:
            file.write(self.to_bytes())
        self.path = path


def find_string_end(data, start):
    position = start
    while position < len(data):
        byte = data[position]
        if byte == END_OF_DIALOGUE_STRING or byte == END_OF_TIMED_STRING:
            break
        if is_control_code(byte):
            position = position + 1 + control_code_argument_count(byte, byte_after(data, position))
        else:
            position = position + 1
    return position


def parse_binl(data, path=None):
    if len(data) < HEADER_LENGTH or data[:len(MAGIC_START)] != MAGIC_START:
        raise ValueError('Not an EvMsg .binl file (bad magic)')
    magic = bytes(data[:MAGIC_LENGTH])
    count = int.from_bytes(data[COUNT_OFFSET:COUNT_OFFSET + COUNT_SIZE], 'little')
    if count > MAX_STRING_COUNT:
        raise ValueError('Implausible string count %d' % count)
    strings = []
    endings = []
    position = HEADER_LENGTH
    for string_number in range(count):
        end = find_string_end(data, position)
        strings.append(bytes(data[position:min(end, len(data))]))
        if end < len(data):
            endings.append(data[end])
        else:
            endings.append(END_OF_DIALOGUE_STRING)
        position = end + 1
    return BinlFile(magic, strings, endings, path, len(data))


def load_binl(path):
    with open(path, 'rb') as file:
        data = file.read()
    return parse_binl(data, path)

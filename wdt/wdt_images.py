"""Decoding the .wdt images (PS2 8bpp with a CLUT) and writing PNGs."""
import struct
import zlib


PALETTE_COLOURS = 256

PALETTE_SIZE = 0x400


def csm1_palette_index(index):
    bits_0_to_2_and_5_to_7 = index & 0xE7
    bit_4_moved_to_3 = (index & 0x10) >> 1
    bit_3_moved_to_4 = (index & 0x08) << 1
    return bits_0_to_2_and_5_to_7 | bit_4_moved_to_3 | bit_3_moved_to_4


def ps2_alpha_to_8bit(alpha):
    return min(255, alpha * 2)


def indexed_to_rgba(pixels: bytes, clut: bytes, swizzled: bool) -> bytes:
    palette = []
    for index in range(PALETTE_COLOURS):
        clut_index = index
        if swizzled:
            clut_index = csm1_palette_index(index)
        red, green, blue, alpha = clut[clut_index * 4:clut_index * 4 + 4]
        palette.append(bytes((red, green, blue, ps2_alpha_to_8bit(alpha))))
    return b''.join(palette[pixel] for pixel in pixels)


def png_chunk(tag, body):
    checksum = zlib.crc32(tag + body) & 0xFFFFFFFF
    return struct.pack('>I', len(body)) + tag + body + struct.pack('>I', checksum)


def png_bytes(width: int, height: int, rgba: bytes) -> bytes:
    row_size = width * 4
    scanlines = []
    for y in range(height):
        scanlines.append(b'\x00' + rgba[y * row_size:(y + 1) * row_size])
    header = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    return (b'\x89PNG\r\n\x1a\n' + png_chunk(b'IHDR', header) +
            png_chunk(b'IDAT', zlib.compress(b''.join(scanlines), 9)) + png_chunk(b'IEND', b''))


def checker_background(x, y):
    if ((x // 8) + (y // 8)) % 2 == 1:
        return 0xCC
    return 0x99


def blend_over(channel, alpha, background):
    return (channel * alpha + background * (255 - alpha)) // 255


def checker_composite(width, height, rgba, scale):
    output = bytearray()
    for y in range(height * scale):
        source_y = y // scale
        for x in range(width * scale):
            source_x = x // scale
            pixel = (source_y * width + source_x) * 4
            red, green, blue, alpha = rgba[pixel:pixel + 4]
            background = checker_background(x, y)
            output += bytes((blend_over(red, alpha, background), blend_over(green, alpha, background),
                             blend_over(blue, alpha, background), 255))
    return png_bytes(width * scale, height * scale, bytes(output))

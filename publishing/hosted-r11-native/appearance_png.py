"""Original-byte PNG checks, adapted only to pinned SE dimensions. No rendering or conversion."""
import hashlib
import struct
import zlib
from typing import Any
PIXEL_SIZE = (750, 1334)
def require(ok, message):
    if not ok: raise ValueError(message)

def inspect_png(data: bytes) -> dict[str, Any]:
    require(33 <= len(data) <= 25_000_000 and data[:8] == b"\x89PNG\r\n\x1a\n",
            "Screenshot is not a bounded original PNG")
    offset, index, ended = 8, 0, False
    compressed = bytearray()
    idat_seen, idat_ended = False, False
    while offset < len(data):
        require(offset + 12 <= len(data), "Truncated PNG chunk")
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        kind = data[offset + 4:offset + 8]
        end = offset + 12 + length
        require(end <= len(data), "PNG chunk exceeds native file")
        payload = data[offset + 8:offset + 8 + length]
        crc = struct.unpack(">I", data[end - 4:end])[0]
        require(zlib.crc32(kind + payload) & 0xffffffff == crc, "PNG chunk CRC mismatch")
        if index == 0:
            require(kind == b"IHDR" and length == 13, "PNG must start with one IHDR")
            require(struct.unpack(">IIBBBBB", payload) == (*PIXEL_SIZE, 8, 2, 0, 0, 0),
                    "Original screenshot must be 750x1334 opaque 8-bit RGB, noninterlaced")
        elif kind == b"IHDR":
            raise ValueError("Duplicate PNG header")
        if kind == b"IDAT":
            require(not idat_ended, "Noncontiguous PNG image data")
            idat_seen = True
            compressed.extend(payload)
        elif idat_seen:
            idat_ended = True
        require(kind not in {b"tRNS", b"acTL", b"fcTL", b"fdAT", b"CgBI"},
                "Transparency, animation or nonstandard screenshot representation is not accepted")
        require(kind in {b"IHDR", b"IDAT", b"IEND", b"PLTE"} or (kind[0] & 32) != 0,
                "Unknown critical PNG chunk")
        if kind == b"IEND":
            require(length == 0 and end == len(data) and idat_seen, "Invalid PNG end")
            ended = True
        offset, index = end, index + 1
    require(ended and compressed, "Incomplete PNG image")
    stride = PIXEL_SIZE[0] * 3 + 1
    expected = stride * PIXEL_SIZE[1]
    decoder = zlib.decompressobj()
    pixels = decoder.decompress(bytes(compressed), expected + 1)
    require(len(pixels) == expected and decoder.eof and not decoder.unconsumed_tail
            and not decoder.unused_data, "PNG decompression does not match its actual dimensions")
    require(all(pixels[row * stride] <= 4 for row in range(PIXEL_SIZE[1])), "Invalid PNG row filter")
    return {"width": PIXEL_SIZE[0], "height": PIXEL_SIZE[1], "color_type": "RGB",
            "alpha_channel": False, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}



SUPPORTED_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".avif")
PNG_EXT = "png"
JPG_EXT = "jpg"
JPEG_EXT = "jpeg"
WEBP_EXT = "webp"
AVIF_EXT = "avif"

SUPPORTED_EXTENSIONS_BIN = (b'\x89PNG\r\n\x1a\n', b'\xff\xd8\xff',
                            b'\xff\xd8\xdd', b'RIFF', b'\x00\x00\x00\x20ftypavif')
PNG_EXT_BIN = b'\x89PNG\r\n\x1a\n'
JPG_EXT_BIN = b'\xff\xd8\xff'
JPEG_EXT_BIN = b'\xff\xd8\xdd'
WEBP_EXT_BIN = b'RIFF'
AVIF_EXT_BIN = b'\x00\x00\x00\x20ftypavif'

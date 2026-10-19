"""Profile photos. Only small JPEG, PNG or WebP images are kept, recognised from their bytes rather than from the
file name or the type the browser claims, so nothing a browser could run as a page (SVG, HTML) is stored or served."""

MAX_BYTES = 512 * 1024  # the app uploads a 256 px square, a few tens of KB


def image_type(data: bytes) -> str | None:
    """The image's media type, or None when it isn't a JPEG, PNG or WebP."""
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None

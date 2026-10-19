from app.services.avatar import image_type


def test_jpeg_png_and_webp_are_recognised_from_their_bytes():
    assert image_type(b"\xff\xd8\xff\xe0" + b"\0" * 20) == "image/jpeg"
    assert image_type(b"\x89PNG\r\n\x1a\n" + b"\0" * 20) == "image/png"
    assert image_type(b"RIFF\x24\0\0\0WEBPVP8 " + b"\0" * 20) == "image/webp"


def test_anything_a_browser_could_run_is_refused():
    assert image_type(b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>') is None
    assert image_type(b"<!doctype html><html></html>") is None
    assert image_type(b"GIF89a" + b"\0" * 20) is None
    assert image_type(b"") is None

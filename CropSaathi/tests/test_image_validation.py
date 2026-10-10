from io import BytesIO

from PIL import Image

from src.image_validation import validate_image


def make_image(
    image_format: str = "PNG",
    size: tuple[int, int] = (100, 100),
    mode: str = "RGB",
) -> bytes:
    image = Image.new(mode, size, color="red")
    output = BytesIO()
    image.save(output, format=image_format)
    return output.getvalue()


def upload(data: bytes, name: str = "leaf.png") -> BytesIO:
    uploaded_file = BytesIO(data)
    uploaded_file.name = name
    return uploaded_file


def test_valid_png_is_accepted():
    result = validate_image(upload(make_image()))

    assert result["ok"] is True
    assert result["reason"] == ""
    assert isinstance(result["image"], Image.Image)


def test_valid_image_is_converted_to_rgb():
    result = validate_image(upload(make_image(mode="RGBA")))

    assert result["ok"] is True
    assert result["image"].mode == "RGB"


def test_supported_formats_are_accepted():
    for image_format, extension in (
        ("JPEG", "leaf.jpg"),
        ("PNG", "leaf.png"),
        ("WEBP", "leaf.webp"),
    ):
        result = validate_image(upload(make_image(image_format), extension))

        assert result["ok"] is True


def test_unsupported_format_is_rejected_even_with_supported_filename():
    result = validate_image(upload(make_image("GIF"), "leaf.png"))

    assert result["ok"] is False
    assert "Unsupported image format" in result["reason"]
    assert result["image"] is None


def test_corrupt_image_is_rejected():
    result = validate_image(upload(b"not an image"))

    assert result["ok"] is False
    assert "corrupt" in result["reason"]
    assert result["image"] is None


def test_empty_input_is_rejected():
    result = validate_image(upload(b""))

    assert result["ok"] is False
    assert "empty" in result["reason"]
    assert result["image"] is None


def test_invalid_input_is_rejected_without_crashing():
    result = validate_image(object())

    assert result == {
        "ok": False,
        "reason": "Invalid image input.",
        "image": None,
    }


def test_oversized_image_is_rejected():
    oversized = BytesIO(b"x" * (5 * 1024 * 1024 + 1))
    oversized.name = "leaf.png"

    result = validate_image(oversized)

    assert result["ok"] is False
    assert "5 MB" in result["reason"]
    assert result["image"] is None


def test_image_below_minimum_dimensions_is_rejected():
    result = validate_image(upload(make_image(size=(99, 100))))

    assert result["ok"] is False
    assert "100 x 100" in result["reason"]
    assert result["image"] is None
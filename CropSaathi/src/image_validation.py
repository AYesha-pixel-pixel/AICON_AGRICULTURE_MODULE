from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

from src.config import ALLOWED_EXTENSIONS, MAX_UPLOAD_MB, MIN_IMAGE_SIZE


_MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
_SUPPORTED_FORMATS = {"JPEG", "PNG", "WEBP"}


def _read_upload(uploaded_file: Any) -> bytes | None:
    if isinstance(uploaded_file, (bytes, bytearray, memoryview)):
        return bytes(uploaded_file)

    getvalue = getattr(uploaded_file, "getvalue", None)
    if callable(getvalue):
        value = getvalue()
        if isinstance(value, (bytes, bytearray, memoryview)):
            return bytes(value)
        return None

    read = getattr(uploaded_file, "read", None)
    if not callable(read):
        return None

    try:
        position = uploaded_file.tell()
    except (AttributeError, OSError):
        position = None

    try:
        uploaded_file.seek(0)
        data = uploaded_file.read(_MAX_UPLOAD_BYTES + 1)
    except (AttributeError, OSError, TypeError, ValueError):
        return None
    finally:
        if position is not None:
            try:
                uploaded_file.seek(position)
            except (AttributeError, OSError, ValueError):
                pass

    if not isinstance(data, (bytes, bytearray, memoryview)):
        return None
    return bytes(data)


def validate_image(uploaded_file: Any) -> dict[str, Any]:
    result = {"ok": False, "reason": "", "image": None}

    if uploaded_file is None:
        result["reason"] = "No image was provided."
        return result

    declared_size = getattr(uploaded_file, "size", None)
    if isinstance(declared_size, int) and declared_size > _MAX_UPLOAD_BYTES:
        result["reason"] = f"Image exceeds the {MAX_UPLOAD_MB} MB upload limit."
        return result

    filename = getattr(uploaded_file, "name", None)
    if isinstance(filename, str) and filename:
        extension = Path(filename).suffix.lower().lstrip(".")
        if extension not in ALLOWED_EXTENSIONS:
            result["reason"] = (
                "Unsupported image format. Please upload JPG, JPEG, PNG, or WebP."
            )
            return result

    data = _read_upload(uploaded_file)
    if data is None:
        result["reason"] = "Invalid image input."
        return result
    if not data:
        result["reason"] = "The uploaded image is empty."
        return result
    if len(data) > _MAX_UPLOAD_BYTES:
        result["reason"] = f"Image exceeds the {MAX_UPLOAD_MB} MB upload limit."
        return result

    try:
        with Image.open(BytesIO(data)) as image:
            image.verify()

        with Image.open(BytesIO(data)) as image:
            if image.format not in _SUPPORTED_FORMATS:
                result["reason"] = (
                    "Unsupported image format. Please upload JPG, JPEG, PNG, or WebP."
                )
                return result
            if image.width < MIN_IMAGE_SIZE[0] or image.height < MIN_IMAGE_SIZE[1]:
                result["reason"] = (
                    f"Image must be at least {MIN_IMAGE_SIZE[0]} x "
                    f"{MIN_IMAGE_SIZE[1]} pixels."
                )
                return result
            converted_image = image.convert("RGB")
    except (OSError, UnidentifiedImageError, ValueError):
        result["reason"] = "The uploaded image is corrupt or cannot be decoded."
        return result

    return {"ok": True, "reason": "", "image": converted_image}
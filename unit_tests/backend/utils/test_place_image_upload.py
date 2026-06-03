from pathlib import Path

import pytest

from backend.utils.place_image_upload import (
    delete_file_for_public_path,
    ensure_place_images_dir,
    public_url_path,
    save_place_image,
)


@pytest.fixture
def place_images_tmp_dir(tmp_path, monkeypatch):
    upload_dir = tmp_path / "uploads" / "place_images"
    monkeypatch.setattr("backend.utils.place_image_upload.PLACE_IMAGES_DIR", upload_dir)
    return upload_dir


def test_ensure_place_images_dir_creates_directory(place_images_tmp_dir):
    ensure_place_images_dir()

    assert place_images_tmp_dir.exists()
    assert place_images_tmp_dir.is_dir()


def test_public_url_path_returns_upload_path():
    result = public_url_path("abc123.jpg")

    assert result == "/uploads/place_images/abc123.jpg"


def test_save_place_image_saves_jpeg_and_returns_public_path(place_images_tmp_dir):
    result = save_place_image(b"fake image bytes", "image/jpeg")

    assert result.startswith("/uploads/place_images/")
    assert result.endswith(".jpg")

    filename = Path(result).name
    saved_file = place_images_tmp_dir / filename

    assert saved_file.exists()
    assert saved_file.read_bytes() == b"fake image bytes"


def test_save_place_image_saves_png_and_returns_public_path(place_images_tmp_dir):
    result = save_place_image(b"fake png bytes", "image/png")

    assert result.startswith("/uploads/place_images/")
    assert result.endswith(".png")

    filename = Path(result).name
    assert (place_images_tmp_dir / filename).read_bytes() == b"fake png bytes"


def test_save_place_image_accepts_content_type_with_charset(place_images_tmp_dir):
    result = save_place_image(b"fake image bytes", "image/jpeg; charset=utf-8")

    assert result.endswith(".jpg")


def test_save_place_image_accepts_uppercase_content_type(place_images_tmp_dir):
    result = save_place_image(b"fake image bytes", "IMAGE/PNG")

    assert result.endswith(".png")


def test_save_place_image_rejects_missing_content_type(place_images_tmp_dir):
    with pytest.raises(ValueError, match="Unsupported image type"):
        save_place_image(b"fake image bytes", None)


def test_save_place_image_rejects_unsupported_content_type(place_images_tmp_dir):
    with pytest.raises(ValueError, match="Unsupported image type"):
        save_place_image(b"fake image bytes", "image/gif")


def test_save_place_image_rejects_file_larger_than_max(place_images_tmp_dir):
    oversized_content = b"x" * (10 * 1024 * 1024 + 1)

    with pytest.raises(ValueError, match="File too large"):
        save_place_image(oversized_content, "image/png")


def test_delete_file_for_public_path_removes_matching_file(place_images_tmp_dir):
    place_images_tmp_dir.mkdir(parents=True)
    file_path = place_images_tmp_dir / "photo.jpg"
    file_path.write_bytes(b"image")

    delete_file_for_public_path("/uploads/place_images/photo.jpg")

    assert not file_path.exists()


def test_delete_file_for_public_path_ignores_none(place_images_tmp_dir):
    delete_file_for_public_path(None)

    assert not place_images_tmp_dir.exists()


def test_delete_file_for_public_path_ignores_paths_outside_place_images(place_images_tmp_dir):
    place_images_tmp_dir.mkdir(parents=True)
    file_path = place_images_tmp_dir / "photo.jpg"
    file_path.write_bytes(b"image")

    delete_file_for_public_path("/uploads/other/photo.jpg")

    assert file_path.exists()


def test_delete_file_for_public_path_ignores_missing_file(place_images_tmp_dir):
    place_images_tmp_dir.mkdir(parents=True)

    delete_file_for_public_path("/uploads/place_images/missing.jpg")

    assert place_images_tmp_dir.exists()


def test_delete_file_for_public_path_prevents_path_traversal(place_images_tmp_dir, tmp_path):
    place_images_tmp_dir.mkdir(parents=True)

    outside_file = tmp_path / "secret.jpg"
    outside_file.write_bytes(b"secret")

    delete_file_for_public_path("/uploads/place_images/../secret.jpg")

    assert outside_file.exists()


def test_delete_file_for_public_path_ignores_nested_path(place_images_tmp_dir):
    place_images_tmp_dir.mkdir(parents=True)
    nested_dir = place_images_tmp_dir / "nested"
    nested_dir.mkdir()
    nested_file = nested_dir / "photo.jpg"
    nested_file.write_bytes(b"image")

    delete_file_for_public_path("/uploads/place_images/nested/photo.jpg")

    assert nested_file.exists()
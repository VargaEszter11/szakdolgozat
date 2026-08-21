from pathlib import Path

import pytest

from backend.utils.feedback_image_upload import (
    delete_feedback_image,
    ensure_feedback_images_dir,
    save_feedback_image,
)


@pytest.fixture
def feedback_images_tmp_dir(tmp_path, monkeypatch):
    upload_dir = tmp_path / "uploads" / "feedback_images"
    monkeypatch.setattr("backend.utils.feedback_image_upload.FEEDBACK_IMAGES_DIR", upload_dir)
    return upload_dir


def test_ensure_feedback_images_dir_creates_directory(feedback_images_tmp_dir):
    ensure_feedback_images_dir()

    assert feedback_images_tmp_dir.exists()
    assert feedback_images_tmp_dir.is_dir()


def test_save_feedback_image_saves_jpeg_and_returns_public_path(feedback_images_tmp_dir):
    result = save_feedback_image(b"fake image bytes", "image/jpeg")

    assert result.startswith("/uploads/feedback_images/")
    assert result.endswith(".jpg")

    filename = Path(result).name
    saved_file = feedback_images_tmp_dir / filename

    assert saved_file.exists()
    assert saved_file.read_bytes() == b"fake image bytes"


def test_save_feedback_image_saves_png_and_returns_public_path(feedback_images_tmp_dir):
    result = save_feedback_image(b"fake png bytes", "image/png")

    assert result.startswith("/uploads/feedback_images/")
    assert result.endswith(".png")

    filename = Path(result).name
    assert (feedback_images_tmp_dir / filename).read_bytes() == b"fake png bytes"


def test_save_feedback_image_accepts_content_type_with_charset(feedback_images_tmp_dir):
    result = save_feedback_image(b"fake image bytes", "image/jpeg; charset=utf-8")

    assert result.endswith(".jpg")


def test_save_feedback_image_accepts_uppercase_content_type(feedback_images_tmp_dir):
    result = save_feedback_image(b"fake image bytes", "IMAGE/PNG")

    assert result.endswith(".png")


def test_save_feedback_image_rejects_missing_content_type(feedback_images_tmp_dir):
    with pytest.raises(ValueError, match="Unsupported image type"):
        save_feedback_image(b"fake image bytes", None)


def test_save_feedback_image_rejects_unsupported_content_type(feedback_images_tmp_dir):
    with pytest.raises(ValueError, match="Unsupported image type"):
        save_feedback_image(b"fake image bytes", "image/gif")


def test_save_feedback_image_rejects_file_larger_than_max(feedback_images_tmp_dir):
    oversized_content = b"x" * (10 * 1024 * 1024 + 1)

    with pytest.raises(ValueError, match="File too large"):
        save_feedback_image(oversized_content, "image/png")


def test_delete_feedback_image_removes_matching_file(feedback_images_tmp_dir):
    feedback_images_tmp_dir.mkdir(parents=True)
    file_path = feedback_images_tmp_dir / "photo.jpg"
    file_path.write_bytes(b"image")

    delete_feedback_image("/uploads/feedback_images/photo.jpg")

    assert not file_path.exists()


def test_delete_feedback_image_ignores_none(feedback_images_tmp_dir):
    delete_feedback_image(None)

    assert not feedback_images_tmp_dir.exists()


def test_delete_feedback_image_ignores_paths_outside_feedback_images(feedback_images_tmp_dir):
    feedback_images_tmp_dir.mkdir(parents=True)
    file_path = feedback_images_tmp_dir / "photo.jpg"
    file_path.write_bytes(b"image")

    delete_feedback_image("/uploads/other/photo.jpg")

    assert file_path.exists()


def test_delete_feedback_image_ignores_missing_file(feedback_images_tmp_dir):
    feedback_images_tmp_dir.mkdir(parents=True)

    delete_feedback_image("/uploads/feedback_images/missing.jpg")

    assert feedback_images_tmp_dir.exists()


def test_delete_feedback_image_prevents_path_traversal(feedback_images_tmp_dir, tmp_path):
    feedback_images_tmp_dir.mkdir(parents=True)

    outside_file = tmp_path / "secret.jpg"
    outside_file.write_bytes(b"secret")

    delete_feedback_image("/uploads/feedback_images/../secret.jpg")

    assert outside_file.exists()


def test_delete_feedback_image_ignores_nested_path(feedback_images_tmp_dir):
    feedback_images_tmp_dir.mkdir(parents=True)
    nested_dir = feedback_images_tmp_dir / "nested"
    nested_dir.mkdir()
    nested_file = nested_dir / "photo.jpg"
    nested_file.write_bytes(b"image")

    delete_feedback_image("/uploads/feedback_images/nested/photo.jpg")

    assert nested_file.exists()

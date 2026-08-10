"""
Integration tests for visited place image endpoints.
"""
import io


class TestPlaceImages:
    """Integration tests for image CRUD on visited places."""

    def test_create_place_image(self, client, visited_place, auth_headers):
        response = client.post(
            f"/api/visited-places/{visited_place['id']}/images",
            headers=auth_headers,
            json={"image_path": "/uploads/place_images/test.jpg"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["image_path"] == "/uploads/place_images/test.jpg"
        assert data["visited_place_id"] == visited_place["id"]

    def test_create_place_image_place_not_found(self, client, auth_headers):
        response = client.post(
            "/api/visited-places/9999/images",
            headers=auth_headers,
            json={"image_path": "/uploads/place_images/test.jpg"},
        )

        assert response.status_code == 404

    def test_upload_place_image(self, client, visited_place, auth_headers):
        png_bytes = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx"
            b"\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01\x00\x05\xfe\xd4\xef"
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        response = client.post(
            f"/api/visited-places/{visited_place['id']}/images/upload",
            headers=auth_headers,
            files={"file": ("photo.png", io.BytesIO(png_bytes), "image/png")},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["image_path"].startswith("/uploads/place_images/")
        assert data["visited_place_id"] == visited_place["id"]

    def test_upload_place_image_invalid_type(self, client, visited_place, auth_headers):
        response = client.post(
            f"/api/visited-places/{visited_place['id']}/images/upload",
            headers=auth_headers,
            files={"file": ("doc.txt", io.BytesIO(b"not an image"), "text/plain")},
        )

        assert response.status_code == 400

    def test_list_place_images(self, client, visited_place, auth_headers):
        client.post(
            f"/api/visited-places/{visited_place['id']}/images",
            headers=auth_headers,
            json={"image_path": "/uploads/place_images/a.jpg"},
        )
        client.post(
            f"/api/visited-places/{visited_place['id']}/images",
            headers=auth_headers,
            json={"image_path": "/uploads/place_images/b.jpg"},
        )

        response = client.get(
            f"/api/visited-places/{visited_place['id']}/images",
            headers=auth_headers,
        )

        assert response.status_code == 200
        images = response.json()
        assert len(images) == 2

    def test_list_place_images_place_not_found(self, client, auth_headers):
        response = client.get("/api/visited-places/9999/images", headers=auth_headers)

        assert response.status_code == 404

    def test_get_image_by_id(self, client, visited_place, auth_headers):
        create_response = client.post(
            f"/api/visited-places/{visited_place['id']}/images",
            headers=auth_headers,
            json={"image_path": "/uploads/place_images/single.jpg"},
        )
        image_id = create_response.json()["id"]

        response = client.get(f"/api/images/{image_id}", headers=auth_headers)

        assert response.status_code == 200
        assert response.json()["id"] == image_id

    def test_get_image_not_found(self, client, auth_headers):
        response = client.get("/api/images/9999", headers=auth_headers)

        assert response.status_code == 404

    def test_update_image(self, client, visited_place, auth_headers):
        create_response = client.post(
            f"/api/visited-places/{visited_place['id']}/images",
            headers=auth_headers,
            json={"image_path": "/uploads/place_images/old.jpg"},
        )
        image_id = create_response.json()["id"]

        response = client.put(
            f"/api/images/{image_id}",
            headers=auth_headers,
            json={"image_path": "/uploads/place_images/new.jpg"},
        )

        assert response.status_code == 200
        assert response.json()["image_path"] == "/uploads/place_images/new.jpg"

    def test_delete_image(self, client, visited_place, auth_headers):
        create_response = client.post(
            f"/api/visited-places/{visited_place['id']}/images",
            headers=auth_headers,
            json={"image_path": "/uploads/place_images/to-delete.jpg"},
        )
        image_id = create_response.json()["id"]

        response = client.delete(f"/api/images/{image_id}", headers=auth_headers)

        assert response.status_code == 204
        assert client.get(f"/api/images/{image_id}", headers=auth_headers).status_code == 404

    def test_delete_image_not_found(self, client, auth_headers):
        response = client.delete("/api/images/9999", headers=auth_headers)

        assert response.status_code == 404

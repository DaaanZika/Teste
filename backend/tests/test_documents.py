import io

import pytest
from PIL import Image

from app.models.enums import DocumentStatus


def _png_bytes(*, text_marker: int = 0) -> bytes:
    image = Image.new("RGB", (40, 20), color=(255, 255, 255))
    # Vary the top-left pixel so different calls produce different file
    # bytes/hashes when needed by a test.
    image.putpixel((0, 0), (text_marker % 255, 0, 0))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_upload_document_success(client):
    content = _png_bytes(text_marker=1)
    response = client.post(
        "/documents/upload",
        files={"file": ("recibo.png", content, "image/png")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["possible_duplicate"] is False
    assert body["document"]["status"] == DocumentStatus.UPLOADED.value
    assert body["document"]["sha256_hash"]
    assert body["document"]["original_filename"] == "recibo.png"


def test_upload_same_file_twice_flags_duplicate_without_creating_new_document(client):
    content = _png_bytes(text_marker=2)

    first = client.post("/documents/upload", files={"file": ("nota.png", content, "image/png")})
    assert first.status_code == 200
    first_id = first.json()["document"]["id"]

    second = client.post("/documents/upload", files={"file": ("nota_copia.png", content, "image/png")})
    assert second.status_code == 200
    second_body = second.json()

    assert second_body["possible_duplicate"] is True
    assert "same_file_hash" in second_body["duplicate_reasons"]
    # No new document row was created for the exact-hash duplicate.
    assert second_body["document"]["id"] == first_id


def test_upload_rejects_unsupported_extension(client):
    response = client.post(
        "/documents/upload",
        files={"file": ("malware.exe", b"conteudo qualquer", "application/octet-stream")},
    )
    assert response.status_code == 415
    body = response.json()
    assert body["success"] is False
    assert body["error"] == "UNSUPPORTED_FILE_TYPE"


def test_upload_rejects_empty_file(client):
    response = client.post(
        "/documents/upload",
        files={"file": ("vazio.png", b"", "image/png")},
    )
    assert response.status_code == 415


def test_process_document_never_crashes_even_without_ocr_engine(client):
    content = _png_bytes(text_marker=3)
    upload = client.post("/documents/upload", files={"file": ("outro.png", content, "image/png")})
    document_id = upload.json()["document"]["id"]

    response = client.post(f"/documents/{document_id}/process")
    assert response.status_code == 200
    body = response.json()
    # Whatever the outcome (OCR engine present or not in this environment),
    # the document must land in a well-defined, non-crashing state.
    assert body["status"] in (
        DocumentStatus.PROCESSED.value,
        DocumentStatus.HUMAN_REVIEW.value,
        DocumentStatus.POSSIBLE_DUPLICATE.value,
    )


def test_get_document_file_returns_original_bytes(client):
    content = _png_bytes(text_marker=4)
    upload = client.post("/documents/upload", files={"file": ("visualizar.png", content, "image/png")})
    document_id = upload.json()["document"]["id"]

    response = client.get(f"/documents/{document_id}/file")
    assert response.status_code == 200
    assert response.content == content
    assert response.headers["content-type"] == "image/png"


def test_get_document_file_404_for_missing_document(client):
    response = client.get("/documents/does-not-exist/file")
    assert response.status_code == 404


def test_get_nonexistent_document_returns_404(client):
    response = client.get("/documents/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"] == "NOT_FOUND"

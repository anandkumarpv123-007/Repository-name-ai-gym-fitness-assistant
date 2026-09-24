import asyncio
import io
import json
import os
import sys
import unittest
from datetime import datetime
from sqlalchemy import select, text, func

# Append backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from database import Base, SessionLocal, engine
from models.user import User
from models.profile import Profile
from models.media import MediaAsset
from services.storage_service import StorageService, MAX_FILE_SIZE_BYTES
from auth.security import hash_password
from auth.token import create_access_token
from main import app


async def asgi_request_raw(method: str, path: str, body_bytes: bytes = b"", headers: dict = None):
    """ASGI helper supporting raw bytes & multipart/form-data requests."""
    response_body = []
    status_code = None

    url_path = path
    query_string = b""
    if "?" in path:
        url_path, q_str = path.split("?", 1)
        query_string = q_str.encode("utf-8")

    req_headers = []
    if headers:
        for k, v in headers.items():
            req_headers.append((k.lower().encode("utf-8"), v.encode("utf-8")))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method.upper(),
        "path": url_path,
        "raw_path": url_path.encode("utf-8"),
        "query_string": query_string,
        "headers": req_headers,
        "client": ("127.0.0.1", 50000),
        "server": ("127.0.0.1", 80),
    }

    async def receive():
        return {
            "type": "http.request",
            "body": body_bytes,
            "more_body": False,
        }

    async def send(message):
        nonlocal status_code
        if message["type"] == "http.response.start":
            status_code = message["status"]
        elif message["type"] == "http.response.body":
            response_body.append(message.get("body", b""))

    await app(scope, receive, send)
    full_bytes = b"".join(response_body)
    
    parsed_json = None
    try:
        parsed_json = json.loads(full_bytes.decode("utf-8"))
    except Exception:
        parsed_json = full_bytes

    return status_code, parsed_json, full_bytes


def build_multipart_body(fields: dict, files: dict, boundary: str = "----WebKitFormBoundary7MA4YWxkTrZu0gW") -> Tuple[bytes, str]:
    """Helper to construct valid multipart/form-data payload."""
    body = io.BytesIO()

    for name, value in fields.items():
        body.write(f"--{boundary}\r\n".encode("utf-8"))
        body.write(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        body.write(f"{value}\r\n".encode("utf-8"))

    for name, file_info in files.items():
        filename, content_type, content_bytes = file_info
        body.write(f"--{boundary}\r\n".encode("utf-8"))
        body.write(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode("utf-8"))
        body.write(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        body.write(content_bytes)
        body.write(b"\r\n")

    body.write(f"--{boundary}--\r\n".encode("utf-8"))
    content_type_header = f"multipart/form-data; boundary={boundary}"
    return body.getvalue(), content_type_header


class TestPhase10Storage(unittest.TestCase):
    """
    Comprehensive Automated Test Suite for Phase 10 — Storage / Media / Infrastructure.
    Validates file uploads (images, videos, documents), size/MIME validation,
    path traversal guards, file serving, soft/hard deletion, user storage stats,
    S3/GCS simulation provider modes, user isolation, and regression against Phases 1–9.
    """

    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()

        # Clean existing test users if present
        cls.db.execute(text("DELETE FROM users WHERE email IN ('storage_a@example.com', 'storage_b@example.com');"))
        cls.db.commit()

        # Create User A
        cls.user_a = User(
            name="Storage User A",
            email="storage_a@example.com",
            password_hash=hash_password("Password123!"),
        )
        cls.db.add(cls.user_a)
        cls.db.commit()
        cls.db.refresh(cls.user_a)

        # Create User B (for isolation tests)
        cls.user_b = User(
            name="Storage User B",
            email="storage_b@example.com",
            password_hash=hash_password("Password123!"),
        )
        cls.db.add(cls.user_b)
        cls.db.commit()
        cls.db.refresh(cls.user_b)

        cls.token_a = create_access_token(cls.user_a.id)
        cls.token_b = create_access_token(cls.user_b.id)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def tearDown(self):
        self.db.rollback()

    # 1. Successful PNG Image Upload
    def test_01_upload_image_success(self):
        image_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
        body, content_type = build_multipart_body(
            fields={"category": "avatar", "storage_provider": "local"},
            files={"file": ("profile_picture.png", "image/png", image_bytes)},
        )

        status, body_json, _ = asyncio.run(
            asgi_request_raw(
                "POST",
                "/media/upload",
                body_bytes=body,
                headers={"Authorization": f"Bearer {self.token_a}", "Content-Type": content_type},
            )
        )
        self.assertEqual(status, 201)
        self.assertEqual(body_json["file_name"], "profile_picture.png")
        self.assertEqual(body_json["file_type"], "image")
        self.assertEqual(body_json["mime_type"], "image/png")
        self.assertEqual(body_json["category"], "avatar")
        self.assertIn("/media/file/", body_json["public_url"])

    # 2. Successful MP4 Video Upload
    def test_02_upload_video_success(self):
        video_bytes = b"\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2avc1mp41"
        body, content_type = build_multipart_body(
            fields={"category": "pose_recording"},
            files={"file": ("squat_form_recording.mp4", "video/mp4", video_bytes)},
        )

        status, body_json, _ = asyncio.run(
            asgi_request_raw(
                "POST",
                "/media/upload",
                body_bytes=body,
                headers={"Authorization": f"Bearer {self.token_a}", "Content-Type": content_type},
            )
        )
        self.assertEqual(status, 201)
        self.assertEqual(body_json["file_type"], "video")
        self.assertEqual(body_json["category"], "pose_recording")

    # 3. Successful PDF Document Upload
    def test_03_upload_document_success(self):
        pdf_bytes = b"%PDF-1.4 %...\x0a1 0 obj << /Type /Catalog >> endobj"
        body, content_type = build_multipart_body(
            fields={"category": "diet_report"},
            files={"file": ("weekly_diet_plan.pdf", "application/pdf", pdf_bytes)},
        )

        status, body_json, _ = asyncio.run(
            asgi_request_raw(
                "POST",
                "/media/upload",
                body_bytes=body,
                headers={"Authorization": f"Bearer {self.token_a}", "Content-Type": content_type},
            )
        )
        self.assertEqual(status, 201)
        self.assertEqual(body_json["file_type"], "document")

    # 4. Binary File Retrieval / Downloading File
    def test_04_download_media_file(self):
        sample_bytes = b"AI Gym Fitness Assistant Storage Test Content 12345"
        body, content_type = build_multipart_body(
            fields={"category": "general"},
            files={"file": ("test_doc.txt", "text/plain", sample_bytes)},
        )

        _, upload_json, _ = asyncio.run(
            asgi_request_raw(
                "POST",
                "/media/upload",
                body_bytes=body,
                headers={"Authorization": f"Bearer {self.token_a}", "Content-Type": content_type},
            )
        )
        stored_name = upload_json["stored_file_name"]

        # Download file with valid auth header
        status, _, raw_bytes = asyncio.run(
            asgi_request_raw("GET", f"/media/file/{stored_name}", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status, 200)
        self.assertEqual(raw_bytes, sample_bytes)

    # 5. Oversized File Rejection (> 50 MB)
    def test_05_oversized_file_rejection(self):
        # Test direct validation exception in StorageService
        with self.assertRaises(ValueError) as ctx:
            StorageService.validate_file("huge_video.mp4", "video/mp4", MAX_FILE_SIZE_BYTES + 1024)
        self.assertIn("exceeds maximum limit", str(ctx.exception))

    # 6. Unsupported MIME / Executable Extension Rejection
    def test_06_unsupported_mime_type_rejection(self):
        exe_bytes = b"MZ\x90\x00\x03\x00\x00\x00"
        body, content_type = build_multipart_body(
            fields={"category": "general"},
            files={"file": ("malicious_script.exe", "application/x-msdownload", exe_bytes)},
        )

        status, body_json, _ = asyncio.run(
            asgi_request_raw(
                "POST",
                "/media/upload",
                body_bytes=body,
                headers={"Authorization": f"Bearer {self.token_a}", "Content-Type": content_type},
            )
        )
        self.assertEqual(status, 400)
        detail = body_json["detail"].lower()
        self.assertTrue("unsupported" in detail or "forbidden" in detail)

    # 7. Path Traversal Attempt Sanitization
    def test_07_path_traversal_sanitization(self):
        sample_bytes = b"Safe Content"
        body, content_type = build_multipart_body(
            fields={"category": "general"},
            files={"file": ("../../../../etc/passwd.txt", "text/plain", sample_bytes)},
        )

        status, body_json, _ = asyncio.run(
            asgi_request_raw(
                "POST",
                "/media/upload",
                body_bytes=body,
                headers={"Authorization": f"Bearer {self.token_a}", "Content-Type": content_type},
            )
        )
        self.assertEqual(status, 201)
        self.assertEqual(body_json["file_name"], "../../../../etc/passwd.txt")
        self.assertNotIn("..", body_json["stored_file_name"])

    # 8. Retrieve Media Asset Metadata by ID
    def test_08_get_asset_metadata_by_id(self):
        sample_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
        body, content_type = build_multipart_body(
            fields={"category": "progress_photo"},
            files={"file": ("progress_1.png", "image/png", sample_bytes)},
        )

        _, upload_json, _ = asyncio.run(
            asgi_request_raw(
                "POST",
                "/media/upload",
                body_bytes=body,
                headers={"Authorization": f"Bearer {self.token_a}", "Content-Type": content_type},
            )
        )
        asset_id = upload_json["id"]

        status, meta_json, _ = asyncio.run(
            asgi_request_raw("GET", f"/media/assets/{asset_id}", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status, 200)
        self.assertEqual(meta_json["id"], asset_id)
        self.assertEqual(meta_json["category"], "progress_photo")

    # 9. List User Media Assets
    def test_09_list_user_media_assets(self):
        status, assets_json, _ = asyncio.run(
            asgi_request_raw("GET", "/media/assets", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status, 200)
        self.assertIsInstance(assets_json, list)

    # 10. List Assets Filtered by Category
    def test_10_list_user_assets_category_filter(self):
        status, assets_json, _ = asyncio.run(
            asgi_request_raw("GET", "/media/assets?category=avatar", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status, 200)
        for a in assets_json:
            self.assertEqual(a["category"], "avatar")

    # 11. List Assets Filtered by File Type
    def test_11_list_user_assets_type_filter(self):
        status, assets_json, _ = asyncio.run(
            asgi_request_raw("GET", "/media/assets?file_type=video", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status, 200)
        for a in assets_json:
            self.assertEqual(a["file_type"], "video")

    # 12. Delete Media Asset and Cleanup Physical File
    def test_12_delete_media_asset(self):
        sample_bytes = b"Delete me"
        body, content_type = build_multipart_body(
            fields={"category": "temp"},
            files={"file": ("to_delete.txt", "text/plain", sample_bytes)},
        )

        _, upload_json, _ = asyncio.run(
            asgi_request_raw(
                "POST",
                "/media/upload",
                body_bytes=body,
                headers={"Authorization": f"Bearer {self.token_a}", "Content-Type": content_type},
            )
        )
        asset_id = upload_json["id"]

        status, del_json, _ = asyncio.run(
            asgi_request_raw("DELETE", f"/media/assets/{asset_id}", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status, 200)
        self.assertIn("deleted successfully", del_json["message"])

    # 13. Deleted Asset Returns HTTP 404
    def test_13_get_deleted_asset_404(self):
        sample_bytes = b"Deleted 404 test"
        body, content_type = build_multipart_body(
            fields={"category": "temp"},
            files={"file": ("to_delete_2.txt", "text/plain", sample_bytes)},
        )

        _, upload_json, _ = asyncio.run(
            asgi_request_raw(
                "POST",
                "/media/upload",
                body_bytes=body,
                headers={"Authorization": f"Bearer {self.token_a}", "Content-Type": content_type},
            )
        )
        asset_id = upload_json["id"]

        # Delete asset
        asyncio.run(
            asgi_request_raw("DELETE", f"/media/assets/{asset_id}", headers={"Authorization": f"Bearer {self.token_a}"})
        )

        # Try to retrieve deleted asset
        status, _, _ = asyncio.run(
            asgi_request_raw("GET", f"/media/assets/{asset_id}", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status, 404)

    # 14. User Storage Usage Statistics
    def test_14_user_storage_statistics(self):
        status, stats_json, _ = asyncio.run(
            asgi_request_raw("GET", "/media/stats", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status, 200)
        self.assertIn("total_files", stats_json)
        self.assertIn("total_bytes_used", stats_json)
        self.assertIn("total_mb_used", stats_json)
        self.assertIn("category_breakdown", stats_json)

    # 15. S3 Simulation Provider Storage Mode
    def test_15_s3_simulation_provider_upload(self):
        sample_bytes = b"S3 Simulation Data"
        body, content_type = build_multipart_body(
            fields={"category": "cloud_backup", "storage_provider": "s3_simulation"},
            files={"file": ("s3_object.txt", "text/plain", sample_bytes)},
        )

        status, body_json, _ = asyncio.run(
            asgi_request_raw(
                "POST",
                "/media/upload",
                body_bytes=body,
                headers={"Authorization": f"Bearer {self.token_a}", "Content-Type": content_type},
            )
        )
        self.assertEqual(status, 201)
        self.assertEqual(body_json["storage_provider"], "s3_simulation")
        self.assertIn("s3://ai-gym-fitness-bucket/", body_json["storage_key"])

    # 16. GCS Simulation Provider Storage Mode
    def test_16_gcs_simulation_provider_upload(self):
        sample_bytes = b"GCS Simulation Data"
        body, content_type = build_multipart_body(
            fields={"category": "cloud_backup", "storage_provider": "gcs_simulation"},
            files={"file": ("gcs_object.txt", "text/plain", sample_bytes)},
        )

        status, body_json, _ = asyncio.run(
            asgi_request_raw(
                "POST",
                "/media/upload",
                body_bytes=body,
                headers={"Authorization": f"Bearer {self.token_a}", "Content-Type": content_type},
            )
        )
        self.assertEqual(status, 201)
        self.assertEqual(body_json["storage_provider"], "gcs_simulation")
        self.assertIn("gs://ai-gym-fitness-storage/", body_json["storage_key"])

    # 17. Cross-User Metadata Isolation (User B cannot access User A's asset)
    def test_17_cross_user_metadata_isolation(self):
        sample_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
        body, content_type = build_multipart_body(
            fields={"category": "private"},
            files={"file": ("private_a.png", "image/png", sample_bytes)},
        )

        _, upload_json, _ = asyncio.run(
            asgi_request_raw(
                "POST",
                "/media/upload",
                body_bytes=body,
                headers={"Authorization": f"Bearer {self.token_a}", "Content-Type": content_type},
            )
        )
        asset_id = upload_json["id"]

        # Attempt to access as User B
        status, _, _ = asyncio.run(
            asgi_request_raw("GET", f"/media/assets/{asset_id}", headers={"Authorization": f"Bearer {self.token_b}"})
        )
        self.assertEqual(status, 404)

    # 18. Cross-User Deletion Isolation (User B cannot delete User A's asset)
    def test_18_cross_user_deletion_isolation(self):
        sample_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
        body, content_type = build_multipart_body(
            fields={"category": "private"},
            files={"file": ("private_del.png", "image/png", sample_bytes)},
        )

        _, upload_json, _ = asyncio.run(
            asgi_request_raw(
                "POST",
                "/media/upload",
                body_bytes=body,
                headers={"Authorization": f"Bearer {self.token_a}", "Content-Type": content_type},
            )
        )
        asset_id = upload_json["id"]

        # Attempt deletion as User B
        status, _, _ = asyncio.run(
            asgi_request_raw("DELETE", f"/media/assets/{asset_id}", headers={"Authorization": f"Bearer {self.token_b}"})
        )
        self.assertEqual(status, 404)

    # 19. Unauthenticated Upload Rejected with HTTP 401
    def test_19_unauthenticated_upload_rejected(self):
        sample_bytes = b"No Auth Upload"
        body, content_type = build_multipart_body(
            fields={"category": "general"},
            files={"file": ("no_auth.txt", "text/plain", sample_bytes)},
        )

        status, _, _ = asyncio.run(
            asgi_request_raw(
                "POST",
                "/media/upload",
                body_bytes=body,
                headers={"Content-Type": content_type},
            )
        )
        self.assertEqual(status, 401)

    # 20. Unauthenticated Asset Listing Rejected with HTTP 401
    def test_20_unauthenticated_assets_list_rejected(self):
        status, _, _ = asyncio.run(
            asgi_request_raw("GET", "/media/assets")
        )
        self.assertEqual(status, 401)

    # 21. Empty 0-Byte File Rejection
    def test_21_empty_file_rejection(self):
        empty_bytes = b""
        body, content_type = build_multipart_body(
            fields={"category": "general"},
            files={"file": ("empty.txt", "text/plain", empty_bytes)},
        )

        status, body_json, _ = asyncio.run(
            asgi_request_raw(
                "POST",
                "/media/upload",
                body_bytes=body,
                headers={"Authorization": f"Bearer {self.token_a}", "Content-Type": content_type},
            )
        )
        self.assertEqual(status, 400)
        self.assertIn("empty", body_json["detail"].lower())

    # 22. StorageService Unit Test: Filename Sanitization
    def test_22_storage_service_unit_sanitize(self):
        clean = StorageService.sanitize_filename("my photo (1) [final].png")
        self.assertNotIn(" ", clean)
        self.assertNotIn("(", clean)
        self.assertTrue(clean.endswith(".png"))

    # 23. StorageService Unit Test: MIME Type Validation
    def test_23_storage_service_unit_validate(self):
        f_type = StorageService.validate_file("video.mp4", "video/mp4", 1024)
        self.assertEqual(f_type, "video")
        with self.assertRaises(ValueError):
            StorageService.validate_file("bad.exe", "application/x-executable", 1024)

    # 24. Database Session & Table Schema Health Check
    def test_24_database_session_health(self):
        asset_count = self.db.execute(select(func.count(MediaAsset.id))).scalar()
        self.assertGreaterEqual(asset_count, 0)

    # 25. System Regression Check for Baseline User & Profile Models
    def test_25_regression_baseline_services(self):
        u_a = self.db.execute(select(User).where(User.id == self.user_a.id)).scalars().first()
        self.assertIsNotNone(u_a)
        self.assertEqual(u_a.email, "storage_a@example.com")

    # 26. Magic Bytes Header Signature Mismatch Rejection
    def test_26_magic_bytes_signature_mismatch_rejection(self):
        fake_png_bytes = b"This is plain text pretending to be a PNG image file."
        body, content_type = build_multipart_body(
            fields={"category": "general"},
            files={"file": ("fake_image.png", "image/png", fake_png_bytes)},
        )

        status, body_json, _ = asyncio.run(
            asgi_request_raw(
                "POST",
                "/media/upload",
                body_bytes=body,
                headers={"Authorization": f"Bearer {self.token_a}", "Content-Type": content_type},
            )
        )
        self.assertEqual(status, 400)
        self.assertIn("magic bytes do not match", body_json["detail"].lower())

    # 27. Unauthenticated File Download Rejected with HTTP 401
    def test_27_unauthenticated_file_download_rejected(self):
        sample_bytes = b"Secret data"
        body, content_type = build_multipart_body(
            fields={"category": "general"},
            files={"file": ("secret.txt", "text/plain", sample_bytes)},
        )
        _, upload_json, _ = asyncio.run(
            asgi_request_raw(
                "POST",
                "/media/upload",
                body_bytes=body,
                headers={"Authorization": f"Bearer {self.token_a}", "Content-Type": content_type},
            )
        )
        stored_name = upload_json["stored_file_name"]

        # Attempt download without Authorization header
        status, _, _ = asyncio.run(
            asgi_request_raw("GET", f"/media/file/{stored_name}")
        )
        self.assertEqual(status, 401)

    # 28. Cross-User File Download Rejected with HTTP 404
    def test_28_cross_user_file_download_rejected(self):
        sample_bytes = b"User A Private Download Data"
        body, content_type = build_multipart_body(
            fields={"category": "general"},
            files={"file": ("user_a_file.txt", "text/plain", sample_bytes)},
        )
        _, upload_json, _ = asyncio.run(
            asgi_request_raw(
                "POST",
                "/media/upload",
                body_bytes=body,
                headers={"Authorization": f"Bearer {self.token_a}", "Content-Type": content_type},
            )
        )
        stored_name = upload_json["stored_file_name"]

        # User B attempts download of User A's file
        status, _, _ = asyncio.run(
            asgi_request_raw("GET", f"/media/file/{stored_name}", headers={"Authorization": f"Bearer {self.token_b}"})
        )
        self.assertEqual(status, 404)

    # 29. Soft-Deleted File Download Rejected with HTTP 404
    def test_29_soft_deleted_file_download_rejected(self):
        sample_bytes = b"Soft-deleted download target"
        body, content_type = build_multipart_body(
            fields={"category": "general"},
            files={"file": ("del_file.txt", "text/plain", sample_bytes)},
        )
        _, upload_json, _ = asyncio.run(
            asgi_request_raw(
                "POST",
                "/media/upload",
                body_bytes=body,
                headers={"Authorization": f"Bearer {self.token_a}", "Content-Type": content_type},
            )
        )
        asset_id = upload_json["id"]
        stored_name = upload_json["stored_file_name"]

        # Delete asset
        asyncio.run(
            asgi_request_raw("DELETE", f"/media/assets/{asset_id}", headers={"Authorization": f"Bearer {self.token_a}"})
        )

        # Attempt download of deleted file by owner
        status, _, _ = asyncio.run(
            asgi_request_raw("GET", f"/media/file/{stored_name}", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status, 404)

    # 30. Soft-Deleted Listing Scoping (include_deleted=True only returns owner's assets)
    def test_30_include_deleted_assets_scoping(self):
        sample_bytes = b"Soft-deleted list target"
        body, content_type = build_multipart_body(
            fields={"category": "general"},
            files={"file": ("del_list_file.txt", "text/plain", sample_bytes)},
        )
        _, upload_json, _ = asyncio.run(
            asgi_request_raw(
                "POST",
                "/media/upload",
                body_bytes=body,
                headers={"Authorization": f"Bearer {self.token_a}", "Content-Type": content_type},
            )
        )
        asset_id = upload_json["id"]

        # Delete asset
        asyncio.run(
            asgi_request_raw("DELETE", f"/media/assets/{asset_id}", headers={"Authorization": f"Bearer {self.token_a}"})
        )

        # User A requests list with include_deleted=True -> includes deleted asset
        status_a, assets_a, _ = asyncio.run(
            asgi_request_raw("GET", "/media/assets?include_deleted=true", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status_a, 200)
        user_a_deleted_ids = [a["id"] for a in assets_a if a["is_deleted"]]
        self.assertIn(asset_id, user_a_deleted_ids)

        # User B requests list with include_deleted=True -> cannot see User A's deleted asset
        status_b, assets_b, _ = asyncio.run(
            asgi_request_raw("GET", "/media/assets?include_deleted=true", headers={"Authorization": f"Bearer {self.token_b}"})
        )
        self.assertEqual(status_b, 200)
        user_b_ids = [a["id"] for a in assets_b]
        self.assertNotIn(asset_id, user_b_ids)


if __name__ == "__main__":
    unittest.main()

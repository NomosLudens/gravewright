import json
import shutil
import tarfile
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import Client, TestCase, override_settings

from gravewright.accounts.models import User

from . import post_session_backup as backup


class PostSessionBackupTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email="backup-owner@example.test",
            name="Backup Owner",
            password="a-long-test-password",
            role="owner",
        )
        self.player = User.objects.create_user(
            email="backup-player@example.test",
            name="Backup Player",
            password="a-long-test-password",
        )
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.media = root / "media"
        self.media.mkdir()
        (self.media / "hero.txt").write_text("real media", encoding="utf-8")
        self.runtime = root / "runtime"
        self.runtime.mkdir()
        self.settings_override = override_settings(MEDIA_ROOT=self.media)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.patches = patch.multiple(
            backup,
            BACKUP_TMP_ROOT=root / "tmp",
            FAILED_BACKUP_ROOT=root / "failed",
            LOCK_PATH=root / "backup.lock",
            RECIPIENT_PATH=root / "recipient.txt",
        )
        self.patches.start()
        self.addCleanup(self.patches.stop)
        (root / "recipient.txt").write_text(
            "age1mdz5fpc6uw6qume3rlgj2qzv8gn8eu6sww7wq6906nkggpr00ytqjqfczp\n",
            encoding="utf-8",
        )

    def _login_owner(self):
        self.client.force_login(self.owner)

    def _success_upload(self, seen):
        def upload(source, name):
            seen["name"] = name
            seen["size"] = source.stat().st_size
            with tarfile.open(source, "r:gz") as archive:
                seen["members"] = sorted(archive.getnames())
                seen["manifest"] = archive.extractfile("MANIFEST.txt").read().decode()
            return {"id": "drive-file-id", "name": name, "size": seen["size"]}

        return upload

    def test_owner_success_contains_snapshot_media_manifest_and_cleans_temp(self):
        self._login_owner()
        seen = {}
        with patch.object(backup, "_encrypt", side_effect=shutil.copyfile), patch.object(
            backup, "_upload_drive", side_effect=self._success_upload(seen)
        ):
            response = self.client.post(
                "/api/admin/backups/post-session", {}, content_type="application/json"
            )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["file_id"], "drive-file-id")
        self.assertTrue(seen["name"].endswith(".tar.gz.age"))
        self.assertIn("gravewright.sqlite3", seen["members"])
        self.assertIn("media/hero.txt", seen["members"])
        self.assertIn("MANIFEST.txt", seen["members"])
        self.assertIn("runtime-config/README.txt", seen["members"])
        self.assertIn("DATABASE_INTEGRITY_CHECK=ok", seen["manifest"])
        self.assertIn("BACKUP_REASON=post-session", seen["manifest"])
        temp_root = Path(self.temp.name) / "tmp"
        self.assertTrue(temp_root.is_dir())
        self.assertFalse(list(temp_root.iterdir()))

    def test_player_cannot_trigger_backup(self):
        self.client.force_login(self.player)
        with patch.object(backup, "create_post_session_backup") as create:
            response = self.client.post(
                "/api/admin/backups/post-session", {}, content_type="application/json"
            )
        self.assertEqual(response.status_code, 403)
        create.assert_not_called()

    def test_endpoint_is_post_only_and_csrf_protected(self):
        self._login_owner()
        self.assertEqual(self.client.get("/api/admin/backups/post-session").status_code, 405)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        response = client.post(
            "/api/admin/backups/post-session", {}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)

    def test_second_backup_is_rejected_by_lock(self):
        self._login_owner()
        with backup._backup_lock():
            response = self.client.post(
                "/api/admin/backups/post-session", {}, content_type="application/json"
            )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"], "backup_in_progress")

    def test_upload_failure_keeps_only_encrypted_retry_artifact(self):
        self._login_owner()
        with patch.object(backup, "_encrypt", side_effect=shutil.copyfile), patch.object(
            backup,
            "_upload_drive",
            side_effect=backup.BackupError("backup_drive_upload_failed"),
        ):
            response = self.client.post(
                "/api/admin/backups/post-session", {}, content_type="application/json"
            )
        self.assertEqual(response.status_code, 502)
        temp_root = Path(self.temp.name) / "tmp"
        self.assertTrue(temp_root.is_dir())
        self.assertFalse(list(temp_root.iterdir()))
        failed = list((Path(self.temp.name) / "failed").glob("*.age"))
        self.assertEqual(len(failed), 1)
        self.assertFalse(list((Path(self.temp.name) / "failed").glob("*.tar.gz")))

    def test_recipient_rejects_secret_key_material(self):
        recipient = Path(self.temp.name) / "recipient.txt"
        recipient.write_text("AGE-SECRET-KEY-DO-NOT-STORE\n", encoding="utf-8")
        with self.assertRaises(backup.BackupError):
            backup._recipient()

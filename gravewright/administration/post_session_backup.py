"""Create one encrypted, verified post-session backup.

The backup is deliberately host-scoped: browser input never supplies a path,
command, recipient, or Drive destination.  The Google bridge refreshes the
existing OAuth token; the upload itself uses that refreshed access token for
the Drive multipart endpoint.
"""

from __future__ import annotations

import fcntl
import hashlib
import http.client
import json
import os
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile
import urllib.parse
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings


DRIVE_FOLDER_ID = "1u0YHaxCxDX05Kz85sLsbVvogh7fcYfvL"
RECIPIENT_PATH = Path("/home/tonyus-dev/gravewright-runtime/backup-age-recipient.txt")
BACKUP_TMP_ROOT = Path("/home/tonyus-dev/gravewright-runtime/backup-tmp")
FAILED_BACKUP_ROOT = Path("/home/tonyus-dev/gravewright-runtime/backup-failed")
LOCK_PATH = Path("/home/tonyus-dev/gravewright-runtime/backup-post-session.lock")
GOOGLE_BRIDGE_URL = "http://127.0.0.1:42630"
GOOGLE_TOKEN_PATH = Path.home() / ".config/kaline-google/token.json"
GOOGLE_API_HOST = "www.googleapis.com"


class BackupError(Exception):
    """A safe, user-facing backup failure without secret or path details."""


class BackupBusy(BackupError):
    """Another post-session backup currently owns the lock."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit() -> str:
    try:
        result = subprocess.run(
            ["/usr/bin/git", "-C", "/home/tonyus-dev/gravewright", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise BackupError("backup_commit_unavailable") from error
    commit = result.stdout.strip()
    if len(commit) != 40 or any(character not in "0123456789abcdef" for character in commit):
        raise BackupError("backup_commit_invalid")
    return commit


def _database_path() -> Path:
    name = settings.DATABASES["default"]["NAME"]
    if name == ":memory:":
        raise BackupError("backup_database_unavailable")
    path = Path(name).resolve()
    if not path.is_file():
        raise BackupError("backup_database_unavailable")
    return path


def _snapshot_database(source: Path, destination: Path) -> None:
    try:
        source_connection = sqlite3.connect(
            f"file:{source}?mode=ro", uri=True, timeout=30
        )
        destination_connection = sqlite3.connect(destination)
        try:
            source_connection.backup(destination_connection)
            result = destination_connection.execute("PRAGMA integrity_check").fetchone()
        finally:
            destination_connection.close()
            source_connection.close()
    except (OSError, sqlite3.Error) as error:
        raise BackupError("backup_snapshot_failed") from error
    if result != ("ok",):
        raise BackupError("backup_integrity_failed")


def _add_tree(archive: tarfile.TarFile, source: Path, target: str) -> None:
    if source.is_symlink():
        raise BackupError("backup_media_symlink")
    archive.add(source, arcname=target, recursive=False)
    if not source.is_dir():
        return
    for child in sorted(source.iterdir(), key=lambda path: path.name):
        if child.is_symlink():
            raise BackupError("backup_media_symlink")
        _add_tree(archive, child, f"{target}/{child.name}")


def _archive_media(source: Path, destination: Path) -> None:
    with tarfile.open(destination, "w:gz") as archive:
        if source.is_dir():
            _add_tree(archive, source, "media")
        else:
            info = tarfile.TarInfo("media")
            info.type = tarfile.DIRTYPE
            info.mode = 0o755
            archive.addfile(info)


def _write_runtime_config(destination: Path) -> None:
    destination.mkdir(mode=0o700)
    (destination / "README.txt").write_text(
        """Gravewright post-session backup runtime contract
FORMAT_VERSION=1
DATABASE_FILE=gravewright.sqlite3
MEDIA_DIRECTORY=media
SECRETS=EXCLUDED
CODE_SOURCE=GitHub commit recorded in MANIFEST.txt
""",
        encoding="utf-8",
    )


def _write_manifest(destination: Path, *, commit: str, database: Path, media_archive: Path, created_at: str) -> None:
    destination.write_text(
        "\n".join(
            [
                "FORMAT_VERSION=1",
                f"CREATED_AT_UTC={created_at}",
                "SOURCE_HOST=kaline-mini",
                f"GRAVEWRIGHT_COMMIT={commit}",
                f"DATABASE_SHA256={_sha256(database)}",
                f"MEDIA_ARCHIVE_SHA256={_sha256(media_archive)}",
                "DATABASE_INTEGRITY_CHECK=ok",
                "BACKUP_REASON=post-session",
                f"DRIVE_FOLDER_ID={DRIVE_FOLDER_ID}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _create_package(temp_dir: Path, *, commit: str, created_at: str) -> Path:
    database = temp_dir / "gravewright.sqlite3"
    media_archive = temp_dir / "media.tar.gz"
    manifest = temp_dir / "MANIFEST.txt"
    runtime_config = temp_dir / "runtime-config"
    package = temp_dir / "gravewright.tar.gz"

    _snapshot_database(_database_path(), database)
    _archive_media(Path(settings.MEDIA_ROOT), media_archive)
    _write_runtime_config(runtime_config)
    _write_manifest(
        manifest,
        commit=commit,
        database=database,
        media_archive=media_archive,
        created_at=created_at,
    )
    with tarfile.open(package, "w:gz") as archive:
        archive.add(database, arcname="gravewright.sqlite3")
        media_root = Path(settings.MEDIA_ROOT)
        if media_root.is_dir():
            _add_tree(archive, media_root, "media")
        else:
            info = tarfile.TarInfo("media")
            info.type = tarfile.DIRTYPE
            info.mode = 0o755
            archive.addfile(info)
        archive.add(manifest, arcname="MANIFEST.txt")
        _add_tree(archive, runtime_config, "runtime-config")
    return package


def _recipient() -> str:
    try:
        values = RECIPIENT_PATH.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise BackupError("backup_recipient_unavailable") from error
    if len(values) != 1 or not values[0].startswith("age1") or any(
        value.startswith("AGE-SECRET-KEY-") for value in values
    ):
        raise BackupError("backup_recipient_invalid")
    return values[0]


def _encrypt(package: Path, destination: Path) -> None:
    age = shutil.which("age")
    if not age:
        raise BackupError("backup_encryption_unavailable")
    try:
        subprocess.run(
            [age, "-r", _recipient(), "-o", str(destination), str(package)],
            check=True,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise BackupError("backup_encryption_failed") from error
    if not destination.is_file() or destination.stat().st_size == 0:
        raise BackupError("backup_encryption_failed")


def _bridge_refresh() -> None:
    query = urllib.parse.urlencode({"q": "trashed = false", "pageSize": "1"})
    try:
        with urllib.request.urlopen(
            f"{GOOGLE_BRIDGE_URL}/api/drive/search?{query}", timeout=30
        ) as response:
            if response.status != 200:
                raise BackupError("backup_drive_authentication_failed")
            response.read()
    except BackupError:
        raise
    except (OSError, ValueError) as error:
        raise BackupError("backup_drive_unavailable") from error


def _access_token() -> str:
    _bridge_refresh()
    try:
        token = json.loads(GOOGLE_TOKEN_PATH.read_text(encoding="utf-8"))
        access_token = token["access_token"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise BackupError("backup_drive_authentication_failed") from error
    if not isinstance(access_token, str) or not access_token:
        raise BackupError("backup_drive_authentication_failed")
    return access_token


def _drive_metadata(file_id: str, token: str) -> dict:
    query = urllib.parse.urlencode(
        {"supportsAllDrives": "true", "fields": "id,name,size,parents"}
    )
    connection = http.client.HTTPSConnection(GOOGLE_API_HOST, timeout=60)
    try:
        connection.request(
            "GET",
            f"/drive/v3/files/{urllib.parse.quote(file_id, safe='')}?{query}",
            headers={"Authorization": f"Bearer {token}"},
        )
        response = connection.getresponse()
        body = response.read()
    finally:
        connection.close()
    if response.status < 200 or response.status >= 300:
        raise BackupError("backup_drive_verification_failed")
    try:
        return json.loads(body)
    except json.JSONDecodeError as error:
        raise BackupError("backup_drive_verification_failed") from error


def _upload_drive(source: Path, name: str) -> dict:
    token = _access_token()
    boundary = f"gravewright-{os.urandom(12).hex()}".encode("ascii")
    metadata = json.dumps(
        {
            "name": name,
            "mimeType": "application/octet-stream",
            "parents": [DRIVE_FOLDER_ID],
        },
        separators=(",", ":"),
    ).encode("utf-8")
    opening = (
        b"--" + boundary + b"\r\n"
        b"Content-Type: application/json; charset=UTF-8\r\n\r\n"
        + metadata
        + b"\r\n--"
        + boundary
        + b"\r\nContent-Type: application/octet-stream\r\n\r\n"
    )
    closing = b"\r\n--" + boundary + b"--\r\n"
    length = len(opening) + source.stat().st_size + len(closing)
    connection = http.client.HTTPSConnection(GOOGLE_API_HOST, timeout=120)
    try:
        query = urllib.parse.urlencode(
            {
                "uploadType": "multipart",
                "supportsAllDrives": "true",
                "fields": "id,name,size,parents",
            }
        )
        connection.putrequest("POST", f"/upload/drive/v3/files?{query}")
        connection.putheader("Authorization", f"Bearer {token}")
        connection.putheader(
            "Content-Type", f"multipart/related; boundary={boundary.decode('ascii')}"
        )
        connection.putheader("Content-Length", str(length))
        connection.endheaders()
        connection.send(opening)
        with source.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                connection.send(chunk)
        connection.send(closing)
        response = connection.getresponse()
        body = response.read()
    finally:
        connection.close()
    if response.status < 200 or response.status >= 300:
        raise BackupError("backup_drive_upload_failed")
    try:
        result = json.loads(body)
    except json.JSONDecodeError as error:
        raise BackupError("backup_drive_upload_failed") from error
    if not result.get("id"):
        raise BackupError("backup_drive_upload_failed")
    verified = _drive_metadata(result["id"], token)
    if verified.get("name") != name or int(verified.get("size", 0)) <= 0:
        raise BackupError("backup_drive_verification_failed")
    if DRIVE_FOLDER_ID not in (verified.get("parents") or []):
        raise BackupError("backup_drive_verification_failed")
    return verified


@contextmanager
def _backup_lock():
    LOCK_PATH.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    handle = LOCK_PATH.open("a+")
    try:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise BackupBusy("backup_in_progress") from error
        yield handle
    finally:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def create_post_session_backup() -> dict:
    """Build, encrypt, upload, verify and clean one post-session backup."""

    with _backup_lock():
        BACKUP_TMP_ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
        temp_dir = Path(tempfile.mkdtemp(prefix="post-session-", dir=BACKUP_TMP_ROOT))
        os.chmod(temp_dir, 0o700)
        encrypted = None
        try:
            created = datetime.now(timezone.utc)
            commit = _git_commit()
            package = _create_package(
                temp_dir,
                commit=commit,
                created_at=created.isoformat().replace("+00:00", "Z"),
            )
            filename = f"gravewright-pos-sessao-{created:%Y%m%d-%H%M%S}-{commit[:8]}.tar.gz.age"
            encrypted = temp_dir / filename
            _encrypt(package, encrypted)
            remote = _upload_drive(encrypted, filename)
            return {
                "file_id": remote["id"],
                "file_name": remote["name"],
                "file_size": int(remote["size"]),
                "database_integrity": "ok",
                "encrypted": True,
                "temporary_unencrypted_files": 0,
            }
        except BackupError:
            if encrypted is not None and encrypted.is_file():
                FAILED_BACKUP_ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
                os.replace(encrypted, FAILED_BACKUP_ROOT / encrypted.name)
            raise
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

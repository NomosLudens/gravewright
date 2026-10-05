"""Regression check for the campaign ZIP input across Inside section navigation."""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
ZIP = Path(
    "/home/tonyus-dev/Portifolio/gravewright/.training/kallistis/sessao-01/"
    "kallistis-system-0.0.1.zip"
)


def free_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def main():
    if not ZIP.is_file():
        raise FileNotFoundError(ZIP)

    output = ROOT / "test-results/file-input-identity"
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="grave-file-input-") as temp:
        env = {
            **os.environ,
            "GRAVEWRIGHT_DATABASE": temp + "/db.sqlite3",
            "GRAVEWRIGHT_MEDIA_ROOT": temp + "/media",
        }
        subprocess.run(
            [sys.executable, "manage.py", "migrate", "--noinput"],
            cwd=ROOT,
            env=env,
            check=True,
            stdout=subprocess.DEVNULL,
        )
        seed = """
import json,os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django;django.setup()
from django.conf import settings
from django.test import Client
from gravewright.accounts.models import User
owner=User.objects.create_user('gm@example.test','password-123',name='GM',role='owner')
client=Client();client.force_login(owner)
print(json.dumps({'cookie':settings.SESSION_COOKIE_NAME,'session':client.session.session_key}))
"""
        auth = json.loads(
            subprocess.check_output([sys.executable, "-c", seed], cwd=ROOT, env=env, text=True)
        )
        port = free_port()
        base = f"http://127.0.0.1:{port}"
        log_path = output / "server.log"
        with log_path.open("w") as log:
            server = subprocess.Popen(
                [sys.executable, "manage.py", "runserver", f"127.0.0.1:{port}", "--noreload"],
                cwd=ROOT,
                env=env,
                stdout=log,
                stderr=log,
            )
            try:
                for _ in range(100):
                    try:
                        urlopen(base, timeout=1).close()
                        break
                    except OSError:
                        time.sleep(0.1)
                else:
                    raise RuntimeError(f"Django did not start; inspect {log_path}")

                with sync_playwright() as pw:
                    browser = pw.chromium.launch()
                    context = browser.new_context()
                    context.add_cookies(
                        [{"name": auth["cookie"], "value": auth["session"], "url": base}]
                    )
                    page = context.new_page()
                    page.goto(base + "/inside?section=administration")
                    uploads = []
                    page.on(
                        "request",
                        lambda request: uploads.append(request.url)
                        if request.method == "POST"
                        and "/api/admin/campaigns/import" in request.url
                        else None,
                    )
                    input_file = page.locator("#administration-import-archive")
                    expect(input_file).to_have_count(1)
                    input_file.set_input_files(str(ZIP))
                    assert input_file.evaluate("el => el.files.length") == 1
                    before = input_file.evaluate(
                        "el => ({id:el.id,name:el.name,count:el.files.length,filename:el.files[0].name,"
                        "parent:el.parentElement.tagName+'[data-form='+el.form?.dataset.form+']',"
                        "container:el.closest('[data-administration]')?.tagName,"
                        "template:'gravewright_web/inside/administration.html'})"
                    )
                    page.evaluate(
                        "() => { window.__fileInputBefore = "
                        "document.querySelector('#administration-import-archive'); "
                        "window.__administrationBefore = document.querySelector('[data-administration]'); }"
                    )

                    page.get_by_role("button", name="Settings", exact=True).click()
                    expect(page.locator(".player-settings")).to_be_visible()
                    page.get_by_role("button", name="Administration", exact=True).click()
                    expect(page.locator("[data-administration]")).to_be_visible()
                    after = page.locator("#administration-import-archive").evaluate(
                        "el => ({id:el.id,name:el.name,count:el.files.length,"
                        "filename:el.files[0]?.name,"
                        "sameElement:el===window.__fileInputBefore,"
                        "sameAdministration:el.closest('[data-administration]')===window.__administrationBefore,"
                        "parent:el.parentElement.tagName+'[data-form='+el.form?.dataset.form+']',"
                        "container:el.closest('[data-administration]')?.tagName})"
                    )
                    assert before["filename"] == ZIP.name, before
                    assert after["count"] == 1, after
                    assert after["filename"] == ZIP.name, after
                    assert after["sameElement"], after
                    assert after["sameAdministration"], after
                    assert not uploads, uploads
                    print("INPUT_BEFORE=" + json.dumps(before), flush=True)
                    print("INPUT_AFTER=" + json.dumps(after), flush=True)
                    print("REGRESSION_TEST=PASS", flush=True)
                    browser.close()
            finally:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()


if __name__ == "__main__":
    main()

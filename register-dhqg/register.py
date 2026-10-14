"""Tạo tài khoản SV5T hàng loạt trên https://youth.vnuhcm.edu.vn/.

Signup chạy bằng patchright + Chrome đang cài (reCAPTCHA chặn Playwright thường
và request thuần). Hồ sơ nominee.info được ghi bằng JSON-RPC của chính session
vừa đăng ký. Tài khoản đã tồn tại chỉ được ghi log và bỏ qua.
"""

from __future__ import annotations

import argparse
import base64
import http.cookiejar
import json
import os
import random
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import openpyxl
from patchright.sync_api import TimeoutError as PlaywrightTimeout
from patchright.sync_api import sync_playwright

BASE = "https://youth.vnuhcm.edu.vn"
SIGNUP_URL = f"{BASE}/web/signup?redirect=%2Fodoo%3F"
HERE = Path(__file__).resolve().parent
PROFILE = Path(os.environ.get("LOCALAPPDATA", HERE)) / "sv5t-youth-register"
AVATAR_FILE = HERE / "avatar-placeholder.jpg"
CHROME_PROFILES_ROOT = Path(os.environ.get("LOCALAPPDATA", HERE)) / "sv5t-chrome-profiles"
_avatar_b64: str | None = None

NOMINEE_TYPE = {
    "Sinh viên": "student",
    "Giảng viên, trợ giảng, nghiên cứu viên": "academic_staff",
    "Cán bộ làm công tác quản lý": "management_staff",
    "Giáo viên trẻ THPT Năng khiếu": "ptnk_staff",
}
GENDER = {"Nam": "male", "Nữ": "female"}
DEGREE = {
    "Sinh viên": "student",
    "Cử nhân/Kỹ sư": "bachelor",
    "Thạc sĩ": "master",
    "Tiến sĩ": "doctor",
}
READ_FIELDS = [
    "id",
    "nominee_name",
    "nominee_id",
    "unit_id",
    "class_name",
    "nominee_type",
    "phone",
    "citizen_id",
    "gender",
    "ethnic",
    "religion",
    "academic_degree",
    "academic_title",
    "dob",
    "regular_address",
    "temp_address",
    "same_address",
]


@dataclass
class Student:
    email: str
    password: str
    name: str
    nominee_id: str
    school: str
    class_name: str
    phone: str
    nominee_type: str
    citizen_id: str
    gender: str
    ethnic: str
    religion: str
    academic_degree: str
    dob: str
    regular_address: str
    temp_address: str
    same_address: bool
    warnings: list[str] = field(default_factory=list)


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def log_line(log_path: Path, status: str, email: str, message: str, *, echo: bool = True) -> None:
    text = " ".join(str(message).split())
    stamp = datetime.now().isoformat(timespec="seconds")
    line = f"{stamp}\t{status}\t{email}\t{text}"
    if echo:
        print(line, flush=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def show_progress(index: int, total: int, status: str, email: str) -> None:
    width = 28
    filled = 0 if total == 0 else round(width * index / total)
    bar = "#" * filled + "-" * (width - filled)
    line = f"[{bar}] {index}/{total} {status} {email}"
    print(f"\r\x1b[2K{line[:140]}", end="", flush=True)


def finish_progress() -> None:
    print("\r\x1b[2K", end="", flush=True)


def digits_only(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if isinstance(value, int):
        return str(value)
    return "".join(ch for ch in str(value).strip() if ch.isdigit())


def as_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def as_bool(value):
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return bool(int(value))
    token = str(value).strip().lower()
    if token in {"true", "1", "yes", "có"}:
        return True
    if token in {"false", "0", "no", "không"}:
        return False
    return None


def majority_text(value, fallback: str):
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if value == 1 or as_text(value) == "1":
        return fallback
    text = as_text(value)
    return text or None


def parse_dob(value):
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = as_text(value)
    parts = text.split("/")
    if len(parts) == 3 and all(part.isdigit() for part in parts):
        day, month, year = (int(part) for part in parts)
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            return None
    return None


def cell_map(headers, row) -> dict:
    values = {}
    for index, header in enumerate(headers):
        values[header] = row[index] if index < len(row) else None
    return values


def load_students(path: Path) -> tuple[list[Student], list[tuple[str, str]]]:
    workbook = openpyxl.load_workbook(path, data_only=True)
    sheet = workbook.active
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return [], [("", "File Excel không có dữ liệu")]
    headers = [as_text(header) for header in rows[0]]
    students = []
    invalid = []
    for raw in rows[1:]:
        if not raw or all(value is None or value == "" for value in raw):
            continue
        record = cell_map(headers, raw)
        email = as_text(record.get("Tài khoản"))
        if not email:
            invalid.append(("", "Thiếu tài khoản"))
            continue
        problems = []
        warnings = []
        name = as_text(record.get("Họ tên"))
        password = as_text(record.get("Mật khẩu"))
        nominee_id = as_text(record.get("Mã số sinh viên/cán bộ")) or as_text(record.get("MSSV"))
        school = as_text(record.get("Trường"))
        class_name = as_text(record.get("Khoa/Phòng/Ban"))
        phone_digits = digits_only(record.get("Số điện thoại"))
        citizen_digits = digits_only(record.get("CMND/CCCD"))
        nominee_type = NOMINEE_TYPE.get(as_text(record.get("Nhóm đối tượng")))
        gender = GENDER.get(as_text(record.get("Giới tính")))
        degree = DEGREE.get(as_text(record.get("Trình độ học vấn")))
        ethnic = majority_text(record.get("Dân tộc"), "Kinh (Việt)")
        religion = majority_text(record.get("Tôn giáo"), "Không")
        dob = parse_dob(record.get("Ngày sinh"))
        regular = as_text(record.get("Địa chỉ thường trú"))
        same_address = as_bool(record.get("Địa chỉ tạm trú trùng địa chỉ thường trú?"))
        temp = as_text(record.get("Địa chỉ tạm trú"))

        if not name:
            problems.append("thiếu họ tên")
        if not password:
            problems.append("thiếu mật khẩu")
        if not nominee_id:
            problems.append("thiếu mã số sinh viên")
        if not school:
            problems.append("thiếu trường")
        if not class_name:
            problems.append("thiếu khoa/phòng/ban")
        if not nominee_type:
            problems.append(f"nhóm đối tượng không hợp lệ: {as_text(record.get('Nhóm đối tượng'))}")
        if not gender:
            problems.append(f"giới tính không hợp lệ: {as_text(record.get('Giới tính'))}")
        if not degree:
            problems.append(f"trình độ không hợp lệ: {as_text(record.get('Trình độ học vấn'))}")
        if not ethnic:
            problems.append("thiếu dân tộc")
        if not religion:
            problems.append("thiếu tôn giáo")
        if not dob:
            problems.append(f"ngày sinh không hợp lệ: {as_text(record.get('Ngày sinh'))}")
        if not regular:
            problems.append("thiếu địa chỉ thường trú")
        if same_address is None:
            problems.append("thiếu cờ địa chỉ tạm trú")
        elif not same_address and not temp:
            problems.append("thiếu địa chỉ tạm trú")

        if not phone_digits:
            problems.append("thiếu số điện thoại")
        elif len(phone_digits) > 10:
            problems.append(f"số điện thoại dài {len(phone_digits)} số")
        else:
            if len(phone_digits) not in {9, 10}:
                warnings.append(f"số điện thoại gốc dài {len(phone_digits)} số, đã thêm 0 cho đủ 10")
            phone_digits = phone_digits.zfill(10)

        if not citizen_digits:
            problems.append("thiếu CMND/CCCD")
        elif len(citizen_digits) > 12:
            problems.append(f"CMND/CCCD dài {len(citizen_digits)} số")
        else:
            if len(citizen_digits) not in {11, 12}:
                warnings.append(f"CMND/CCCD gốc dài {len(citizen_digits)} số, đã thêm 0 cho đủ 12")
            citizen_digits = citizen_digits.zfill(12)

        if problems:
            invalid.append((email, "; ".join(problems)))
            continue
        students.append(
            Student(
                email=email,
                password=password,
                name=name,
                nominee_id=nominee_id,
                school=school,
                class_name=class_name,
                phone=phone_digits,
                nominee_type=nominee_type,
                citizen_id=citizen_digits,
                gender=gender,
                ethnic=ethnic,
                religion=religion,
                academic_degree=degree,
                dob=dob,
                regular_address=regular,
                temp_address=regular if same_address else temp,
                same_address=same_address,
                warnings=warnings,
            )
        )
    return students, invalid


def rpc(page, path: str, params: dict):
    response = page.request.post(
        f"{BASE}{path}",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"jsonrpc": "2.0", "method": "call", "params": params, "id": 1}),
        timeout=60_000,
    )
    body = response.json()
    if body.get("error"):
        data = body["error"].get("data") or {}
        message = data.get("message") or body["error"].get("message") or "Odoo lỗi"
        raise RuntimeError(message)
    return body.get("result")


def call_kw(page, model: str, method: str, args, kwargs=None):
    return rpc(
        page,
        f"/web/dataset/call_kw/{model}/{method}",
        {"model": model, "method": method, "args": args, "kwargs": kwargs or {}},
    )


def signup_outcome(page, student: Student) -> tuple[str, str]:
    page.goto(SIGNUP_URL, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_selector("form.oe_signup_form", timeout=30_000)
    page.wait_for_function("() => window.grecaptcha && window.grecaptcha.execute", timeout=30_000)
    page.mouse.move(430, 340)
    page.locator("#login").press_sequentially(student.email, delay=30)
    page.locator("#name").press_sequentially(student.name, delay=30)
    page.locator("#password").press_sequentially(student.password, delay=30)
    page.locator("#confirm_password").press_sequentially(student.password, delay=30)
    page.locator("form.oe_signup_form button[type=submit]").click()
    page.wait_for_function(
        """() => {
            const alert = document.querySelector('p.alert');
            if (alert && alert.textContent.trim()) return true;
            return !location.pathname.includes('/web/signup');
        }""",
        timeout=40_000,
    )
    alert = page.locator("p.alert")
    message = alert.inner_text().strip() if alert.count() else ""
    lowered = message.lower()
    if "already registered" in lowered or "đã đăng ký" in lowered or "đã có người dùng" in lowered:
        return "exists", message
    if "recaptcha" in lowered or "suspicious activity" in lowered:
        return "captcha", message
    if message:
        return "error", message
    if "/web/signup" in page.url:
        return "error", "Không rời được trang đăng ký"
    return "ok", page.url


def resolve_unit(caller, cache: dict, school: str) -> int:
    if school in cache:
        return cache[school]
    if isinstance(caller, SiteSession):
        found = caller.rpc(
            "/web/dataset/call_kw/unit.info/name_search",
            {
                "model": "unit.info",
                "method": "name_search",
                "args": [school],
                "kwargs": {"operator": "ilike", "limit": 20},
            },
        )
    else:
        found = call_kw(caller, "unit.info", "name_search", [school], {"operator": "ilike", "limit": 20})
    exact = [item for item in found if item[1] == school]
    chosen = exact or found
    if not chosen:
        raise RuntimeError(f"Không thấy đơn vị: {school}")
    cache[school] = chosen[0][0]
    return cache[school]


def ensure_avatar() -> Path:
    if AVATAR_FILE.exists() and AVATAR_FILE.stat().st_size >= 1_050_000:
        return AVATAR_FILE
    try:
        import random

        from PIL import Image
    except ImportError as exc:
        raise SystemExit(
            "Web bắt ảnh đại diện >= 1 MB. Đặt file register-dhqg/avatar-placeholder.jpg hoặc cài pillow."
        ) from exc
    random.seed(0)
    width, height = 2400, 1800
    image = Image.new("RGB", (width, height))
    pixels = image.load()
    for y in range(height):
        for x in range(width):
            pixels[x, y] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    image.save(AVATAR_FILE, format="JPEG", quality=100)
    if AVATAR_FILE.stat().st_size < 1_050_000:
        raise SystemExit("Không tạo được avatar-placeholder.jpg đủ 1 MB.")
    return AVATAR_FILE


def avatar_b64() -> str:
    global _avatar_b64
    if _avatar_b64 is None:
        _avatar_b64 = base64.b64encode(ensure_avatar().read_bytes()).decode()
    return _avatar_b64


def profile_values(student: Student, unit_id: int) -> dict:
    return {
        "nominee_name": student.name,
        "nominee_id": student.nominee_id,
        "unit_id": unit_id,
        "class_name": student.class_name,
        "nominee_type": student.nominee_type,
        "phone": student.phone,
        "citizen_id": student.citizen_id,
        "gender": student.gender,
        "ethnic": student.ethnic,
        "religion": student.religion,
        "academic_degree": student.academic_degree,
        "academic_title": "none",
        "dob": student.dob,
        "regular_address": student.regular_address,
        "temp_address": student.temp_address,
        "same_address": student.same_address,
    }


def profile_payload(student: Student, unit_id: int, *, with_avatar: bool) -> dict:
    values = profile_values(student, unit_id)
    if with_avatar:
        values["image_original"] = avatar_b64()
    return values


def profile_diffs(expected: dict, actual: dict) -> list[str]:
    diffs = []
    for key, want in expected.items():
        if key.startswith("image"):
            continue
        got = actual.get(key)
        if key == "unit_id":
            got_id = got[0] if isinstance(got, (list, tuple)) else got
            if got_id != want:
                diffs.append(f"unit_id web={got_id} excel={want}")
            continue
        if key == "same_address":
            if bool(got) != bool(want):
                diffs.append(f"same_address web={got} excel={want}")
            continue
        if (got or "") != want:
            diffs.append(f"{key} web={got!r} excel={want!r}")
    return diffs


def save_profile(page, student: Student, unit_cache: dict) -> str:
    info = rpc(page, "/web/session/get_session_info", {})
    username = (info.get("username") or "").lower()
    if username != student.email.lower():
        raise RuntimeError(f"Session đang là {info.get('username')}, không phải {student.email}")
    uid = info["uid"]
    unit_id = resolve_unit(page, unit_cache, student.school)
    values = profile_payload(student, unit_id, with_avatar=True)
    existing = call_kw(
        page,
        "nominee.info",
        "search_read",
        [[["user_id", "=", uid]]],
        {"fields": ["id"], "limit": 1},
    )
    if existing:
        record_id = existing[0]["id"]
        call_kw(page, "nominee.info", "write", [[record_id], values])
    else:
        record_id = call_kw(
            page,
            "nominee.info",
            "create",
            [{**values, "user_id": uid}],
            {"context": {"default_user_id": uid}},
        )
        if isinstance(record_id, list):
            record_id = record_id[0]
    saved = call_kw(
        page,
        "nominee.info",
        "read",
        [[record_id], READ_FIELDS],
    )
    if not saved:
        raise RuntimeError(f"Không đọc lại được hồ sơ {record_id}")
    diffs = profile_diffs(values, saved[0])
    if diffs:
        raise RuntimeError("Hồ sơ lệch: " + ", ".join(diffs))
    note = f"id={record_id}"
    if student.warnings:
        note += ". " + "; ".join(student.warnings)
    return note


def chrome_profile(use_daily: bool) -> Path:
    return PROFILE


def launch_context(playwright, use_daily: bool):
    if use_daily:
        return None
    profile = chrome_profile(False)
    profile.mkdir(parents=True, exist_ok=True)
    # Cờ AutomationControlled bị reCAPTCHA nhận ra. Truyền một blink feature khác
    # để patchright không tự gắn lại cờ đó.
    return playwright.chromium.launch_persistent_context(
        str(profile),
        channel="chrome",
        headless=False,
        no_viewport=True,
        ignore_default_args=["--disable-blink-features=AutomationControlled"],
        args=["--disable-blink-features=CalculateNativeWinOcclusion"],
    )


class CdpPage:
    def __init__(self, socket):
        self.socket = socket
        self.msg_id = 0
        self.session_id = None

    def call(self, method: str, params=None, session=True, optional=False):
        self.msg_id += 1
        message = {"id": self.msg_id, "method": method, "params": params or {}}
        if session and self.session_id:
            message["sessionId"] = self.session_id
        self.socket.send(json.dumps(message))
        deadline = time.time() + 30
        while time.time() < deadline:
            self.socket.settimeout(max(1, deadline - time.time()))
            payload = json.loads(self.socket.recv())
            if payload.get("id") != self.msg_id:
                continue
            if payload.get("error"):
                message_text = payload["error"].get("message") or "Chrome lỗi"
                if optional and "navigated or closed" in message_text:
                    return {}
                raise RuntimeError(message_text)
            return payload.get("result") or {}
        raise RuntimeError(f"Chrome không trả lời {method}")

    def goto(self, url: str) -> None:
        self.call("Page.navigate", {"url": url}, optional=True)
        deadline = time.time() + 30
        last = None
        stable = 0
        while time.time() < deadline:
            state = self.evaluate("document.readyState + ' ' + location.href")
            if state == last and str(state).startswith("complete"):
                stable += 1
                if stable >= 2:
                    return
            else:
                stable = 0
                last = state
            time.sleep(0.4)
        raise RuntimeError("Trang không tải xong")

    def evaluate(self, expression: str):
        for _ in range(5):
            result = self.call(
                "Runtime.evaluate",
                {"expression": expression, "returnByValue": True, "awaitPromise": True},
                optional=True,
            )
            if result.get("exceptionDetails"):
                time.sleep(0.4)
                continue
            return result.get("result", {}).get("value")
        raise RuntimeError("Trang trả lỗi khi chạy script")

    def url(self) -> str:
        return self.evaluate("location.href") or ""


def warm_up_signup_session(page: CdpPage) -> None:
    page.goto(f"{BASE}/web/login")
    time.sleep(random.uniform(2.5, 5.5))
    try:
        page.evaluate(
            """(() => {
                window.scrollBy(0, 120 + Math.random() * 240);
                return true;
            })()"""
        )
    except RuntimeError:
        pass
    time.sleep(random.uniform(1.2, 3.0))


def signup_connection_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return (
        "10054" in text
        or "10053" in text
        or "forcibly closed" in text
        or ("connection" in text and "abort" in text)
    )


def signup_with_cdp(page: CdpPage, student: Student) -> tuple[str, str]:
    warm_up_signup_session(page)
    page.goto(SIGNUP_URL)
    ready = page.evaluate(
        """new Promise((resolve) => {
            const started = Date.now();
            const tick = () => {
                if (document.querySelector('form.oe_signup_form') && window.grecaptcha && window.grecaptcha.execute) {
                    resolve(true);
                } else if (Date.now() - started > 30000) {
                    resolve(false);
                } else {
                    setTimeout(tick, 300);
                }
            };
            tick();
        })"""
    )
    if not ready:
        return "captcha", "Không thấy form đăng ký hoặc reCAPTCHA"
    try:
        page.evaluate(
            f"""(() => {{
                const values = {json.dumps({"email": student.email, "name": student.name, "password": student.password}, ensure_ascii=False)};
                const set = (selector, value) => {{
                    const node = document.querySelector(selector);
                    node.focus();
                    node.value = value;
                    node.dispatchEvent(new Event('input', {{bubbles: true}}));
                    node.dispatchEvent(new Event('change', {{bubbles: true}}));
                }};
                set('#login', values.email);
                set('#name', values.name);
                const password = document.querySelector('#password');
                const confirm = document.querySelector('#confirm_password');
                password.focus();
                document.execCommand('insertText', false, values.password);
                confirm.focus();
                document.execCommand('insertText', false, values.password);
                document.querySelector('form.oe_signup_form button[type=submit]').click();
                return true;
            }})()"""
        )
    except RuntimeError:
        pass
    deadline = time.time() + 45
    stable_url = ""
    while time.time() < deadline:
        try:
            raw = page.evaluate(
                """(() => JSON.stringify({
                    url: location.href,
                    message: (document.querySelector('p.alert') || {textContent: ''}).textContent.trim()
                }))()"""
            )
        except RuntimeError:
            time.sleep(0.4)
            continue
        if not raw:
            time.sleep(0.4)
            continue
        state = json.loads(raw)
        message = " ".join(str(state.get("message") or "").split())
        url = state.get("url") or ""
        kind = signup_status(message, url if url == stable_url else "")
        stable_url = url
        if kind:
            return kind
        time.sleep(0.4)
    return "captcha", "Hết thời gian chờ reCAPTCHA hoặc trang đăng ký"


def signup_status(message: str, url: str) -> tuple[str, str] | None:
    lowered = message.lower()
    if "already registered" in lowered or "đã đăng ký" in lowered or "đã có người dùng" in lowered:
        return "exists", message
    if "recaptcha" in lowered or "suspicious activity" in lowered or "đáng ngờ" in lowered:
        return "captcha", message
    if message:
        return "error", message
    if url and "/web/signup" not in url and not url.startswith("about:"):
        return "ok", url
    return None


def prepare_chrome_profile(target: Path | None = None) -> Path:
    source = Path(os.environ["LOCALAPPDATA"]) / "Google" / "Chrome" / "User Data"
    target = target or (Path(os.environ["LOCALAPPDATA"]) / "sv5t-chrome-profile")
    if not source.exists():
        raise SystemExit("Không thấy profile Chrome. Cài Google Chrome rồi chạy lại.")
    if target.exists():
        shutil.rmtree(target)
    default = target / "Default"
    default.mkdir(parents=True)
    local_state = source / "Local State"
    if local_state.exists():
        shutil.copy2(local_state, target / "Local State")
    for name in (
        "Cookies",
        "Network",
        "Preferences",
        "Secure Preferences",
        "History",
        "Bookmarks",
        "Local Storage",
        "Session Storage",
        "Favicons",
        "Web Data",
        "Login Data",
    ):
        item = source / "Default" / name
        if not item.exists():
            continue
        destination = default / name
        if item.is_dir():
            shutil.copytree(item, destination)
        else:
            shutil.copy2(item, destination)
    return target


def discover_chrome_profiles(spec: str | None) -> list[Path]:
    if spec:
        root = Path(spec)
        if not root.exists():
            raise SystemExit(f"Không thấy thư mục Chrome profile: {root}")
        if (root / "Default").exists() or (root / "Local State").exists():
            return [root]
        found = sorted(path for path in root.iterdir() if path.is_dir())
        if found:
            return found
        raise SystemExit(f"Không có profile con trong {root}")
    default = Path(os.environ["LOCALAPPDATA"]) / "sv5t-chrome-profile"
    if (default / "Default").exists():
        return [default]
    print("Đang sao profile Chrome hàng ngày...", flush=True)
    return [prepare_chrome_profile(default)]


def kill_chrome_for_profile(profile: Path) -> None:
    marker = str(profile).lower()
    try:
        output = subprocess.check_output(
            ["wmic", "process", "where", "name='chrome.exe'", "get", "ProcessId,CommandLine", "/format:csv"],
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return
    for line in output.splitlines():
        if marker not in line.lower():
            continue
        parts = line.rsplit(",", 1)
        if len(parts) == 2 and parts[1].strip().isdigit():
            subprocess.run(
                ["taskkill", "/PID", parts[1].strip(), "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )


def open_chrome_debug(profile: Path, port: int = 9333) -> subprocess.Popen:
    kill_chrome_for_profile(profile)
    chrome = Path(os.environ["PROGRAMFILES"]) / "Google" / "Chrome" / "Application" / "chrome.exe"
    process = subprocess.Popen(
        [
            str(chrome),
            f"--remote-debugging-port={port}",
            "--remote-allow-origins=*",
            f"--user-data-dir={profile}",
            "--profile-directory=Default",
            "--no-first-run",
            "--no-default-browser-check",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=2) as response:
                json.loads(response.read().decode())
            return process
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            pass
        time.sleep(0.5)
    error = ""
    if process.poll() is not None:
        error = (process.stderr.read() or "").strip()
    raise SystemExit(error or "Không mở được Chrome ở cổng debug. Đóng hết cửa sổ Chrome rồi chạy lại.")


def connect_cdp_page(port: int):
    import websocket

    request = urllib.request.Request(f"http://127.0.0.1:{port}/json/new?about:blank", method="PUT")
    with urllib.request.urlopen(request, timeout=10) as response:
        created = json.loads(response.read().decode())
    browser = websocket.create_connection(created["webSocketDebuggerUrl"], timeout=60, suppress_origin=True)
    page = CdpPage(browser)
    page.call("Page.enable")
    page.call("Runtime.enable")
    return page, browser


def register_with_daily_chrome(
    students: list[Student],
    log_path: Path,
    counts: Counter,
    pause: float = 0,
    profiles: list[Path] | None = None,
    batch_size: int = 7,
    captcha_retries: int = 5,
    refresh_profile: bool = False,
) -> None:
    profiles = profiles or discover_chrome_profiles(None)
    profile_index = 0
    done_on_profile = 0
    page = None
    browser = None
    active_profile = None
    port = 9333

    def start_browser(*, refresh: bool = False) -> None:
        nonlocal page, browser, active_profile, done_on_profile
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass
        if active_profile is not None:
            kill_chrome_for_profile(active_profile)
        active_profile = profiles[profile_index % len(profiles)]
        if refresh and refresh_profile:
            print(f"Làm mới cookie Chrome từ profile hàng ngày → {active_profile.name}", flush=True)
            prepare_chrome_profile(active_profile)
        print(f"Chrome profile: {active_profile.name}", flush=True)
        open_chrome_debug(active_profile, port)
        deadline = time.time() + 25
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=2) as response:
                    json.loads(response.read().decode())
                break
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
                time.sleep(0.5)
        else:
            raise SystemExit("Không mở được Chrome debug. Đóng hết cửa sổ Chrome rồi chạy lại.")
        page, browser = connect_cdp_page(port)
        done_on_profile = 0

    def rotate_profile(reason: str, *, refresh: bool = False) -> None:
        nonlocal profile_index
        if len(profiles) > 1:
            profile_index = (profile_index + 1) % len(profiles)
        print(reason, flush=True)
        start_browser(refresh=refresh)

    start_browser(refresh=refresh_profile)
    total = len(students)
    captcha_streak = 0
    try:
        for index, student in enumerate(students, start=1):
            if index > 1 and pause:
                time.sleep(pause + random.uniform(0, min(15.0, pause * 0.4)))
            show_progress(index - 1, total, "đang đăng ký", student.email)
            last = ""
            status = "captcha_error"
            attempts = max(2, captcha_retries)
            for attempt in range(attempts):
                if attempt:
                    wait = 25 + attempt * 20 + random.uniform(0, 12)
                    time.sleep(wait)
                try:
                    kind, detail = signup_with_cdp(page, student)
                except Exception as exc:
                    if signup_connection_error(exc):
                        last = str(exc)
                        rotate_profile("Mất kết nối Chrome CDP, mở lại trình duyệt...", refresh=refresh_profile)
                        kind, detail = "captcha", last
                    else:
                        kind, detail = "error", str(exc)
                if kind == "captcha":
                    last = detail
                    rotate_profile(
                        f"reCAPTCHA chưa qua (lần {attempt + 1}/{attempts}), đổi phiên Chrome...",
                        refresh=refresh_profile and len(profiles) == 1,
                    )
                    continue
                if kind == "exists":
                    try:
                        note = fill_existing_profile(student, {})
                    except Exception as exc:
                        log_line(log_path, "profile_error", student.email, str(exc), echo=False)
                        counts["profile_error"] += 1
                        status = "profile_error"
                    else:
                        log_line(log_path, "updated", student.email, note, echo=False)
                        counts["updated"] += 1
                        status = "updated"
                elif kind == "error":
                    log_line(log_path, "signup_error", student.email, detail, echo=False)
                    counts["signup_error"] += 1
                    status = "signup_error"
                else:
                    try:
                        note = fill_existing_profile(student, {})
                    except Exception as exc:
                        log_line(log_path, "profile_error", student.email, f"Tài khoản đã tạo nhưng ghi hồ sơ lỗi: {exc}", echo=False)
                        counts["profile_error"] += 1
                        status = "profile_error"
                    else:
                        log_line(log_path, "created", student.email, note, echo=False)
                        counts["created"] += 1
                        status = "created"
                break
            else:
                log_line(log_path, "captcha_error", student.email, last or "reCAPTCHA không qua", echo=False)
                counts["captcha_error"] += 1
            if status == "captcha_error":
                captcha_streak += 1
            else:
                captcha_streak = 0
            if status in {"created", "updated"}:
                done_on_profile += 1
            show_progress(index, total, status, student.email)
            if done_on_profile >= batch_size and index < total:
                rotate_profile(f"Đã đăng ký {batch_size} tài khoản trên profile này, đổi profile...")
        finish_progress()
    finally:
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass
        if active_profile is not None:
            kill_chrome_for_profile(active_profile)


def reset_site_session(context) -> None:
    try:
        context.clear_cookies(domain="youth.vnuhcm.edu.vn")
    except TypeError:
        context.clear_cookies()


def fill_existing_profile(student: Student, unit_cache: dict) -> str:
    session, info = login_account(student)
    uid = info["uid"]
    unit_id = resolve_unit(session, unit_cache, student.school)
    existing = session.rpc(
        "/web/dataset/call_kw/nominee.info/search_read",
        {
            "model": "nominee.info",
            "method": "search_read",
            "args": [[["user_id", "=", uid]]],
            "kwargs": {"fields": ["id", "image_1920"], "limit": 1},
        },
    )
    if existing:
        record_id = existing[0]["id"]
        current = session.rpc(
            "/web/dataset/call_kw/nominee.info/read",
            {
                "model": "nominee.info",
                "method": "read",
                "args": [[record_id], ["nominee_type", "image_1920"]],
                "kwargs": {},
            },
        )
        updates = profile_payload(student, unit_id, with_avatar=not (current[0].get("image_1920") if current else None))
        locked = (current[0].get("nominee_type") if current else None)
        if locked:
            updates.pop("nominee_type", None)
        values = profile_values(student, unit_id)
        session.rpc(
            "/web/dataset/call_kw/nominee.info/write",
            {
                "model": "nominee.info",
                "method": "write",
                "args": [[record_id], updates],
                "kwargs": {},
            },
        )
        if locked:
            values["nominee_type"] = locked
    else:
        values = profile_payload(student, unit_id, with_avatar=True)
        record_id = session.rpc(
            "/web/dataset/call_kw/nominee.info/create",
            {
                "model": "nominee.info",
                "method": "create",
                "args": [{**values, "user_id": uid}],
                "kwargs": {"context": {"default_user_id": uid}},
            },
        )
        if isinstance(record_id, list):
            record_id = record_id[0]
    saved = session.rpc(
        "/web/dataset/call_kw/nominee.info/read",
        {
            "model": "nominee.info",
            "method": "read",
            "args": [[record_id], READ_FIELDS],
            "kwargs": {},
        },
    )
    if not saved:
        raise RuntimeError(f"Không đọc lại được hồ sơ {record_id}")
    diffs = profile_diffs(values, saved[0])
    if diffs:
        raise RuntimeError("Hồ sơ lệch: " + ", ".join(diffs))
    note = f"id={record_id}"
    if student.warnings:
        note += ". " + "; ".join(student.warnings)
    return note


def fill_existing_profiles(students: list[Student], log_path: Path, counts: Counter, workers: int) -> None:
    unit_cache = {}
    cache_lock = threading.Lock()
    progress_lock = threading.Lock()
    done = 0
    total = len(students)

    def worker(student: Student) -> tuple[str, str]:
        local_cache = {}
        with cache_lock:
            if student.school in unit_cache:
                local_cache[student.school] = unit_cache[student.school]
        note = fill_existing_profile(student, local_cache)
        with cache_lock:
            unit_cache.update(local_cache)
        return "updated", note

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(worker, student): student for student in students}
        for future in as_completed(futures):
            student = futures[future]
            try:
                status, detail = future.result()
            except Exception as exc:
                status, detail = "profile_error", str(exc)
            with progress_lock:
                log_line(log_path, status, student.email, detail, echo=False)
                counts[status] += 1
                done += 1
                show_progress(done, total, status, student.email)
    finish_progress()


def process_student(context, student: Student, unit_cache: dict, log_path: Path, counts: Counter) -> str:
    last_captcha = ""
    for attempt in range(2):
        if attempt:
            time.sleep(30)
        reset_site_session(context)
        page = context.new_page()
        try:
            try:
                kind, detail = signup_outcome(page, student)
            except PlaywrightTimeout:
                kind, detail = "captcha", "Hết thời gian chờ reCAPTCHA hoặc trang đăng ký"
            if kind == "captcha":
                last_captcha = detail
                continue
            if kind == "exists":
                log_line(log_path, "skipped", student.email, detail, echo=False)
                counts["skipped"] += 1
                return "skipped"
            if kind == "error":
                log_line(log_path, "signup_error", student.email, detail, echo=False)
                counts["signup_error"] += 1
                return "signup_error"
            try:
                note = save_profile(page, student, unit_cache)
            except Exception as exc:
                log_line(
                    log_path,
                    "profile_error",
                    student.email,
                    f"Tài khoản đã tạo nhưng ghi hồ sơ lỗi: {exc}",
                    echo=False,
                )
                counts["profile_error"] += 1
                return "profile_error"
            log_line(log_path, "created", student.email, note, echo=False)
            counts["created"] += 1
            return "created"
        except Exception as exc:
            log_line(log_path, "signup_error", student.email, str(exc), echo=False)
            counts["signup_error"] += 1
            return "signup_error"
        finally:
            page.close()
    log_line(log_path, "captcha_error", student.email, last_captcha or "reCAPTCHA không qua", echo=False)
    counts["captcha_error"] += 1
    return "captcha_error"


class SiteSession:
    def __init__(self):
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def _open(self, request):
        with self.opener.open(request, timeout=60) as response:
            return response.geturl(), response.read()

    def get(self, url: str) -> tuple[str, str]:
        final, raw = self._open(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}))
        return final, raw.decode("utf-8", "replace")

    def post_form(self, url: str, data: dict) -> tuple[str, str]:
        body = urllib.parse.urlencode(data).encode()
        request = urllib.request.Request(
            url,
            data=body,
            headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/x-www-form-urlencoded"},
        )
        final, raw = self._open(request)
        return final, raw.decode("utf-8", "replace")

    def rpc(self, path: str, params: dict):
        payload = json.dumps({"jsonrpc": "2.0", "method": "call", "params": params, "id": 1}).encode()
        request = urllib.request.Request(
            f"{BASE}{path}",
            data=payload,
            headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"},
        )
        _final, raw = self._open(request)
        body = json.loads(raw.decode())
        if body.get("error"):
            data = body["error"].get("data") or {}
            message = data.get("message") or body["error"].get("message") or "Odoo lỗi"
            raise RuntimeError(message)
        return body.get("result")


def login_account(student: Student) -> tuple[SiteSession, dict]:
    session = SiteSession()
    _url, html = session.get(f"{BASE}/web/login")
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    if not match:
        raise RuntimeError("Không lấy được csrf đăng nhập")
    final, html = session.post_form(
        f"{BASE}/web/login",
        {
            "csrf_token": match.group(1),
            "login": student.email,
            "password": student.password,
            "redirect": "/odoo",
            "type": "password",
        },
    )
    if "/web/login" in final or "Wrong login" in html or "Sai mật khẩu" in html:
        raise LookupError("Chưa có tài khoản")
    info = session.rpc("/web/session/get_session_info", {})
    username = (info.get("username") or "").lower()
    if not info.get("uid") or username != student.email.lower():
        raise LookupError("Không đăng nhập được")
    return session, info


def validate_student(student: Student) -> tuple[str, str]:
    try:
        session, info = login_account(student)
    except LookupError as exc:
        return "missing_account", str(exc)
    records = session.rpc(
        "/web/dataset/call_kw/nominee.info/search_read",
        {
            "model": "nominee.info",
            "method": "search_read",
            "args": [[["user_id", "=", info["uid"]]]],
            "kwargs": {"fields": READ_FIELDS, "limit": 1},
        },
    )
    if not records:
        return "missing_profile", "Đã có tài khoản nhưng chưa có hồ sơ"
    actual = records[0]
    expected = profile_values(student, 0)
    expected.pop("unit_id")
    for key in ("phone", "citizen_id"):
        if same_number(expected.get(key), actual.get(key)):
            expected[key] = actual.get(key) or ""
    diffs = profile_diffs(expected, actual)
    unit = actual.get("unit_id")
    unit_name = unit[1] if isinstance(unit, (list, tuple)) and len(unit) > 1 else ""
    if unit_name != student.school:
        diffs.append(f"unit_id web={unit_name!r} excel={student.school!r}")
    if diffs:
        return "mismatch", "id={}: {}".format(actual.get("id"), ", ".join(diffs))
    return "ok", f"id={actual.get('id')}"


def same_number(left, right) -> bool:
    return str(left or "").lstrip("0") == str(right or "").lstrip("0")


def default_workers() -> int:
    logical = os.cpu_count() or 4
    return max(4, min(8, logical - 4))


def validate_students(
    students: list[Student],
    invalid: list[tuple[str, str]],
    log_path: Path,
    workers: int,
) -> int:
    counts = Counter()
    fields = Counter()
    total = len(students)
    for email, reason in invalid:
        log_line(log_path, "invalid_data", email, reason, echo=False)
        counts["invalid_data"] += 1
    lock = threading.Lock()
    done = 0
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(validate_student, student): student for student in students}
        for future in as_completed(futures):
            student = futures[future]
            try:
                status, detail = future.result()
            except Exception as exc:
                status, detail = "login_error", str(exc)
            with lock:
                log_line(log_path, status, student.email, detail, echo=False)
                counts[status] += 1
                if status == "mismatch":
                    for name in re.findall(r"([a-z_]+) web=", detail):
                        fields[name] += 1
                done += 1
                show_progress(done, total, status, student.email)
    finish_progress()
    print(f"Chi tiết: {log_path}")
    labels = {
        "ok": "khớp Excel",
        "missing_account": "chưa có tài khoản",
        "missing_profile": "có tài khoản, chưa có hồ sơ",
        "mismatch": "có tài khoản, hồ sơ khác Excel",
        "invalid_data": "dòng Excel lỗi",
        "login_error": "lỗi khi đăng nhập",
    }
    for status, count in sorted(counts.items()):
        print(f"  {labels.get(status, status)}: {count}")
    if fields:
        detail = ", ".join(f"{name}={count}" for name, count in fields.most_common())
        print(f"  Trường lệch: {detail}")
    failed = sum(count for name, count in counts.items() if name != "ok")
    return 0 if failed == 0 else 3


def parse_args():
    parser = argparse.ArgumentParser(description="Tạo tài khoản SV5T ĐHQG-HCM từ data.xlsx")
    parser.add_argument("--data", type=Path, default=HERE / "data.xlsx", help="File Excel nguồn")
    parser.add_argument("--log", type=Path, default=None, help="File log")
    parser.add_argument("--limit", type=int, default=0, help="Chỉ xử lý N dòng đầu sau khi bỏ dòng trống")
    parser.add_argument(
        "--use-chrome-profile",
        action="store_true",
        help="Dùng bản sao profile Chrome hàng ngày. Điểm reCAPTCHA cao hơn Chrome mới.",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Đăng nhập từng tài khoản và đối chiếu hồ sơ với data.xlsx, không tạo mới.",
    )
    parser.add_argument(
        "--fill-existing",
        action="store_true",
        help="Đăng nhập các tài khoản đã có và ghi lại hồ sơ từ Excel, không mở Chrome.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=default_workers(),
        help="Số luồng kiểm tra song song. Mặc định chừa CPU cho Chrome.",
    )
    parser.add_argument(
        "--status",
        default="",
        help="Chỉ xử lý email có trạng thái này ở cuối validate.log, ví dụ missing_account.",
    )
    parser.add_argument(
        "--pause",
        type=float,
        default=0,
        help="Số giây nghỉ giữa hai lần đăng ký để giảm bị reCAPTCHA chặn.",
    )
    parser.add_argument(
        "--chrome-profiles",
        type=str,
        default="",
        help="Thư mục chứa nhiều user-data-dir Chrome (mỗi Google account một thư mục con).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=7,
        help="Số tài khoản tạo trên một profile Chrome trước khi đổi profile.",
    )
    parser.add_argument(
        "--captcha-retries",
        type=int,
        default=5,
        help="Số lần thử đăng ký khi gặp reCAPTCHA trước khi bỏ qua dòng.",
    )
    parser.add_argument(
        "--refresh-chrome-profile",
        action="store_true",
        help="Sao lại cookie từ Chrome hàng ngày trước khi mở trình duyệt (và sau mỗi lần bị reCAPTCHA nếu chỉ có một profile).",
    )
    return parser.parse_args()


def run_signup(context, students: list[Student], log_path: Path, counts: Counter) -> None:
    unit_cache = {}
    total = len(students)
    for index, student in enumerate(students, start=1):
        show_progress(index - 1, total, "đang đăng ký", student.email)
        status = process_student(context, student, unit_cache, log_path, counts)
        show_progress(index, total, status, student.email)
    finish_progress()


def main() -> int:
    configure_stdout()
    args = parse_args()
    if args.log is None:
        if args.validate:
            args.log = HERE / "validate.log"
        elif args.fill_existing:
            args.log = HERE / "fill.log"
        else:
            args.log = HERE / "register.log"
    if not args.data.exists():
        print(f"Không thấy file dữ liệu: {args.data}", file=sys.stderr)
        return 1
    students, invalid = load_students(args.data)
    if args.status:
        latest = {}
        validate_log = HERE / "validate.log"
        if validate_log.exists():
            for line in validate_log.read_text(encoding="utf-8").splitlines():
                parts = line.split("\t")
                if len(parts) >= 3:
                    latest[parts[2]] = parts[1]
        students = [student for student in students if latest.get(student.email) == args.status]
        invalid = []
        print(f"Còn {len(students)} tài khoản trạng thái {args.status}.", flush=True)
    if args.limit > 0:
        students = students[: args.limit]
    if args.validate and args.fill_existing:
        print("Chỉ chọn một trong --validate hoặc --fill-existing.", file=sys.stderr)
        return 1
    if args.validate:
        return validate_students(students, invalid, args.log, args.workers)
    if args.fill_existing:
        counts = Counter()
        for email, reason in invalid:
            log_line(args.log, "invalid_data", email, reason, echo=False)
            counts["invalid_data"] += 1
        if students:
            fill_existing_profiles(students, args.log, counts, args.workers)
        summary = ", ".join(f"{name}={count}" for name, count in sorted(counts.items()))
        print(f"Xong: {summary}")
        print(f"Chi tiết: {args.log}")
        return 0 if not counts["profile_error"] else 2
    counts = Counter()
    for email, reason in invalid:
        log_line(args.log, "invalid_data", email, reason)
        counts["invalid_data"] += 1
    if not students and not invalid:
        print("Không có dòng nào để xử lý.")
        return 0
    if students:
        if args.use_chrome_profile:
            profiles = discover_chrome_profiles(args.chrome_profiles or None)
            register_with_daily_chrome(
                students,
                args.log,
                counts,
                args.pause,
                profiles,
                max(1, args.batch_size),
                max(2, args.captcha_retries),
                args.refresh_chrome_profile,
            )
        else:
            with sync_playwright() as playwright:
                context = launch_context(playwright, False)
                try:
                    run_signup(context, students, args.log, counts)
                finally:
                    context.close()
    summary = ", ".join(f"{name}={count}" for name, count in sorted(counts.items()))
    print(f"Xong: {summary}")
    return 0 if not (counts["signup_error"] or counts["captcha_error"] or counts["profile_error"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())

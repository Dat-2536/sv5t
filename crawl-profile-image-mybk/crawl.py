"""Tải ảnh thẻ sinh viên từ myBk HCMUT theo danh sách MSSV trong data.xlsx."""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import http.cookiejar
import openpyxl
import urllib.error
import urllib.parse
import urllib.request

HERE = Path(__file__).resolve().parent
DATA_FILE = HERE / "data.xlsx"
ENV_FILE = HERE / ".env"
OUT_DIR = HERE / "Ảnh thẻ"
LOG_FILE = HERE / "crawl.log"

LIST_URL = (
    "https://mybk.hcmut.edu.vn/app/he-thong-quan-ly-hoc-vu/quan-ly-sinh-vien/danh-sach-sinh-vien"
)
CAS_START = "https://mybk.hcmut.edu.vn/app/login?type=cas"
API_BASE = "https://mybk.hcmut.edu.vn/api/"
IMAGE_PATH = "public/media/hinh-the-4x6/{mssv}/original/v1"


@dataclass
class Row:
    mssv: str
    full_name: str
    image_name: str


class Session:
    def __init__(self) -> None:
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def request(
        self,
        url: str,
        *,
        data: bytes | None = None,
        method: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[str, bytes]:
        base_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) sv5t-mybk-crawl"}
        if headers:
            base_headers.update(headers)
        req = urllib.request.Request(url, data=data, headers=base_headers, method=method)
        with self.opener.open(req, timeout=120) as resp:
            return resp.geturl(), resp.read()


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip()
    return out


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


def log_line(status: str, mssv: str, message: str, *, echo: bool = True) -> None:
    text = " ".join(str(message).split())
    stamp = datetime.now().isoformat(timespec="seconds")
    line = f"{stamp}\t{status}\t{mssv}\t{text}"
    if echo:
        print(line, flush=True)
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def traceparent() -> str:
    return f"00-{uuid.uuid4().hex}-{uuid.uuid4().hex[:16]}-01"


def cas_login(session: Session, account: str, password: str) -> None:
    final, body = session.request(CAS_START)
    html = body.decode("utf-8", "replace")
    if "sso.hcmut.edu.vn/cas/login" not in final:
        raise RuntimeError(f"Không chuyển tới CAS: {final}")
    action = re.search(r'<form id="fm1"[^>]*action="([^"]+)"', html)
    lt = re.search(r'name="lt"\s+value="([^"]+)"', html)
    execution = re.search(r'name="execution"\s+value="([^"]+)"', html)
    if not action or not lt or not execution:
        raise RuntimeError("Thiếu trường form CAS")
    post_url = urljoin(final, action.group(1).replace("&amp;", "&"))
    payload = urllib.parse.urlencode(
        {
            "username": account,
            "password": password,
            "lt": lt.group(1),
            "execution": execution.group(1),
            "_eventId": "submit",
            "submit": "Login",
        }
    ).encode()
    final2, body2 = session.request(post_url, data=payload)
    text2 = body2.decode("utf-8", "replace").lower()
    if "authentication has failed" in text2 or "đăng nhập thất bại" in text2:
        raise RuntimeError("Sai tài khoản hoặc mật khẩu CAS")
    if "sso.hcmut.edu.vn/cas/login" in final2:
        raise RuntimeError("Đăng nhập CAS không thành công")


def fetch_api_token(session: Session) -> str:
    _, body = session.request(LIST_URL)
    html = body.decode("utf-8", "replace")
    if 'id="hid_Token"' not in html:
        raise RuntimeError("Không lấy được token API (chưa đăng nhập hoặc hết quyền)")
    match = re.search(r'id="hid_Token"\s+value="([^"]+)"', html)
    if not match:
        raise RuntimeError("Không parse được hid_Token")
    return match.group(1)


class MyBkClient:
    def __init__(self, account: str, password: str) -> None:
        self.account = account
        self.password = password
        self.session = Session()
        self.token = ""
        self.login()

    def login(self) -> None:
        cas_login(self.session, self.account, self.password)
        self.token = fetch_api_token(self.session)

    def api_get_json(self, path: str) -> dict:
        url = API_BASE + path.lstrip("/")
        headers = {
            "Authorization": self.token,
            "Accept": "application/json",
            "Accept-Language": "vi",
            "Content-Type": "application/json",
            "traceparent": traceparent(),
        }
        try:
            _, raw = self.session.request(url, headers=headers)
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                self.login()
                headers["Authorization"] = self.token
                headers["traceparent"] = traceparent()
                _, raw = self.session.request(url, headers=headers)
            else:
                raise
        return json.loads(raw.decode("utf-8", "replace"))

    def fetch_card_image(self, mssv: str) -> bytes:
        path = IMAGE_PATH.format(mssv=mssv)
        data = self.api_get_json(path)
        code = str(data.get("code", ""))
        if code != "200":
            raise RuntimeError(data.get("msg") or f"API trả mã {code}")
        payload = data.get("data")
        if not isinstance(payload, str) or not payload.startswith("data:image"):
            raise RuntimeError("Không có ảnh thẻ")
        if "," not in payload:
            raise RuntimeError("Định dạng ảnh không hợp lệ")
        return base64.b64decode(payload.split(",", 1)[1])


def load_rows(limit: int) -> list[Row]:
    wb = openpyxl.load_workbook(DATA_FILE, read_only=True, data_only=True)
    ws = wb.active
    rows: list[Row] = []
    for idx, record in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not record:
            continue
        mssv = digits_only(record[1] if len(record) > 1 else "")
        full_name = as_text(record[4] if len(record) > 4 else "")
        image_name = as_text(record[5] if len(record) > 5 else "")
        if not mssv:
            continue
        if not image_name:
            image_name = f"{mssv}_Ảnh thẻ_{full_name or mssv}"
        rows.append(Row(mssv=mssv, full_name=full_name, image_name=image_name))
        if limit and len(rows) >= limit:
            break
    return rows


def output_path(row: Row) -> Path:
    name = row.image_name
    if not name.lower().endswith((".jpg", ".jpeg", ".png")):
        name += ".jpg"
    return OUT_DIR / name


def run(limit: int, skip_existing: bool) -> int:
    env = load_env(ENV_FILE)
    account = env.get("ACCOUNT", "")
    password = env.get("PASSWORD", "")
    if not account or not password:
        print("Thiếu ACCOUNT/PASSWORD trong crawl-profile-image-mybk/.env", file=sys.stderr)
        return 2

    rows = load_rows(limit)
    if not rows:
        print("Không có dòng hợp lệ trong data.xlsx", file=sys.stderr)
        return 2

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    client = MyBkClient(account, password)

    ok = fail = skip = 0
    total = len(rows)
    for index, row in enumerate(rows, start=1):
        dest = output_path(row)
        if skip_existing and dest.exists() and dest.stat().st_size > 0:
            skip += 1
            log_line("skip", row.mssv, dest.name)
            print(f"\r[{index}/{total}] skip {row.mssv}", end="", flush=True)
            continue
        try:
            image = client.fetch_card_image(row.mssv)
            if len(image) < 500:
                raise RuntimeError("Ảnh quá nhỏ, có thể rỗng")
            dest.write_bytes(image)
            ok += 1
            log_line("ok", row.mssv, f"{dest.name} ({len(image)} bytes)")
            print(f"\r[{index}/{total}] ok   {row.mssv} -> {dest.name}", end="", flush=True)
        except Exception as exc:
            fail += 1
            log_line("error", row.mssv, str(exc))
            print(f"\r[{index}/{total}] fail {row.mssv}: {exc}", end="", flush=True)

    print()
    summary = f"Xong: {ok} ok, {fail} lỗi, {skip} bỏ qua (đã có file), tổng {total}"
    print(summary)
    log_line("summary", "-", summary, echo=False)
    return 1 if fail else 0


def main() -> None:
    configure_stdout()
    parser = argparse.ArgumentParser(description="Tải ảnh thẻ sinh viên từ myBk HCMUT")
    parser.add_argument("--limit", type=int, default=0, help="Chỉ xử lý N dòng đầu (0 = tất cả)")
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Bỏ qua nếu file đích trong folder 'Ảnh thẻ' đã tồn tại",
    )
    args = parser.parse_args()
    raise SystemExit(run(args.limit, args.skip_existing))


if __name__ == "__main__":
    main()

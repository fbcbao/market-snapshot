"""Fetch the DSH 1024Store catalog into local JSON pages.

The upstream (deepseek1024.com, Cloudflare) is intermittent from this network,
so each page is tried over several routes and saved independently (resume).
"""
import json
import os
import socket
import ssl
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

HOST = "deepseek1024.com"
PATH = "/api/v2/plugins"
LIMIT = 200
HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
os.makedirs(RAW, exist_ok=True)

ROUTES = [
    (socket.AF_INET6, "2606:4700:3031::6815:579a"),
    (socket.AF_INET6, "2606:4700:3030::ac43:9020"),
    (socket.AF_INET, "104.21.87.154"),
    (socket.AF_INET, "172.67.144.32"),
]
CTX = ssl.create_default_context()
LOCK = threading.Lock()
ROUTE_STATE = {r: {"ok": 0, "fail": 0} for r in ROUTES}


def _recv_all(ss, deadline):
    buf = b""
    while True:
        if time.time() > deadline:
            raise TimeoutError("deadline")
        chunk = ss.recv(65536)
        if not chunk:
            return buf
        buf += chunk


def _dechunk(body):
    out = b""
    while True:
        line, _, rest = body.partition(b"\r\n")
        if not line:
            return out
        size = int(line.split(b";")[0], 16)
        if size == 0:
            return out
        out += rest[:size]
        body = rest[size + 2:]


def http_get(route, path, timeout=25):
    family, ip = route
    s = socket.socket(family, socket.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect((ip, 443) if family == socket.AF_INET else (ip, 443, 0, 0))
    ss = CTX.wrap_socket(s, server_hostname=HOST)
    req = (
        f"GET {path} HTTP/1.1\r\nHost: {HOST}\r\n"
        "User-Agent: dsh-market-snapshot/1.0\r\n"
        "Accept: application/json\r\nConnection: close\r\n\r\n"
    )
    ss.sendall(req.encode())
    raw = _recv_all(ss, time.time() + timeout)
    ss.close()
    head, _, body = raw.partition(b"\r\n\r\n")
    status = head.split(b"\r\n")[0].decode("latin1")
    if " 200 " not in status:
        raise RuntimeError(f"http status {status}")
    if b"transfer-encoding: chunked" in head.lower():
        body = _dechunk(body)
    return json.loads(body)


def page_path(n):
    return os.path.join(RAW, f"page-{n:04d}.json")


def valid(n):
    p = page_path(n)
    if not os.path.exists(p):
        return False
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        return isinstance(d.get("plugins"), list)
    except Exception:
        return False


def fetch_page(n, attempts=10):
    if valid(n):
        return n, "cached", 0.0
    path = f"{PATH}?page={n}&limit={LIMIT}"
    last = None
    t0 = time.time()
    for attempt in range(attempts):
        route = ROUTES[(n + attempt) % len(ROUTES)]
        try:
            data = http_get(route, path, timeout=20)
            with open(page_path(n), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            with LOCK:
                ROUTE_STATE[route]["ok"] += 1
            return n, "ok", time.time() - t0
        except Exception as e:  # noqa: BLE001
            last = e
            with LOCK:
                ROUTE_STATE[route]["fail"] += 1
            time.sleep(0.4)
    return n, f"FAIL {type(last).__name__}: {last}", time.time() - t0


def main():
    first = page_path(1)
    if not valid(1):
        n, state, dt = fetch_page(1, attempts=20)
        print(f"page 1: {state} {dt:.1f}s", flush=True)
        if not valid(1):
            print("cannot reach catalog at all; aborting", flush=True)
            return 1
    with open(first, encoding="utf-8") as f:
        meta = json.load(f)
    total_pages = int(meta.get("totalPages") or 1)
    print(f"total={meta.get('total')} totalPages={total_pages} limit={meta.get('limit')}", flush=True)

    todo = [n for n in range(2, total_pages + 1) if not valid(n)]
    print(f"pending pages: {len(todo)}", flush=True)
    done = 0
    failed = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        for n, state, dt in ex.map(lambda x: fetch_page(x), todo):
            done += 1
            if state.startswith("FAIL"):
                failed.append(n)
                print(f"[{done}/{len(todo)}] page {n}: {state}", flush=True)
            elif done % 5 == 0 or done == len(todo):
                print(f"[{done}/{len(todo)}] page {n}: {state} {dt:.1f}s", flush=True)

    if failed:
        print(f"retrying {len(failed)} failed pages", flush=True)
        still = []
        for n in failed:
            _, state, dt = fetch_page(n, attempts=15)
            if state.startswith("FAIL"):
                still.append(n)
        failed = still
    stats = {f"{ip}": v for (_, ip), v in ROUTE_STATE.items()}
    print("route stats:", json.dumps(stats), flush=True)
    print(f"FAILED PAGES: {failed if failed else 'none'}", flush=True)
    return 0 if not failed else 2


if __name__ == "__main__":
    sys.exit(main())

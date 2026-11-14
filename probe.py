"""Probe the market catalog reachability per route (IPv4 / IPv6 Cloudflare edges)."""
import json
import os
import socket
import ssl
import time

HOST = "deepseek1024.com"
PATH = "/api/v2/plugins?page=1&limit=5"
CTX = ssl.create_default_context()

ROUTES = [
    ("v4", socket.AF_INET, "172.67.144.32"),
    ("v4", socket.AF_INET, "104.21.87.154"),
    ("v6", socket.AF_INET6, "2606:4700:3031::6815:579a"),
    ("v6", socket.AF_INET6, "2606:4700:3030::ac43:9020"),
]


def probe(label, family, ip, timeout=15):
    t0 = time.time()
    try:
        s = socket.socket(family, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((ip, 443) if family == socket.AF_INET else (ip, 443, 0, 0))
        conn = time.time() - t0
        ss = CTX.wrap_socket(s, server_hostname=HOST)
        tls = time.time() - t0 - conn
        req = (
            f"GET {PATH} HTTP/1.1\r\nHost: {HOST}\r\nUser-Agent: dsh-probe\r\n"
            "Accept: application/json\r\nConnection: close\r\n\r\n"
        )
        ss.sendall(req.encode())
        buf = b""
        while True:
            c = ss.recv(65536)
            if not c:
                break
            buf += c
        ss.close()
        head, _, body = buf.partition(b"\r\n\r\n")
        status = head.split(b"\r\n")[0].decode("latin1")
        t = time.time() - t0
        print(f"{label:4} {ip:32} conn={conn:5.2f}s tls={tls:5.2f}s total={t:6.2f}s {status} body={len(body)}B")
        return t
    except Exception as e:  # noqa: BLE001
        print(f"{label:4} {ip:32} FAIL {time.time()-t0:6.2f}s {type(e).__name__}: {str(e)[:50]}")
        return None


if __name__ == "__main__":
    print("NODE_OPTIONS =", os.environ.get("NODE_OPTIONS", "<unset>"))
    print("HTTPS_PROXY  =", os.environ.get("HTTPS_PROXY", "<unset>"))
    print()
    ok6 = ok4 = 0
    for label, family, ip in ROUTES:
        r = probe(label, family, ip)
        if r is not None:
            if label == "v6":
                ok6 += 1
            else:
                ok4 += 1
    print(f"\nsummary: ipv6 {ok6}/2 ok, ipv4 {ok4}/2 ok")

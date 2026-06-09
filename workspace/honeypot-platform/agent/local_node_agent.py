import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SERVER_URL = os.getenv("HONEYPOT_SERVER_URL", "http://localhost:8000").rstrip("/")
ACCESS_TOKEN = os.getenv("HONEYPOT_ACCESS_TOKEN", "")
HONEYZXC_PATH = Path(os.getenv("HONEYZXC_PATH", "../Honeyzxc")).resolve()
POLL_SECONDS = int(os.getenv("HONEYPOT_AGENT_POLL_SECONDS", "5"))
DEFAULT_USERNAME = os.getenv("HONEYPOT_DEFAULT_USERNAME", "zxc")
DEFAULT_PASSWORD = os.getenv("HONEYPOT_DEFAULT_PASSWORD", "clown")

LOG_FILES = {
    "ssh": HONEYZXC_PATH / "logs" / "sessions.jsonl",
    "http": HONEYZXC_PATH / "logs" / "http_sessions.jsonl",
}


class AgentError(Exception):
    pass


def request_json(path, method="GET", payload=None):
    if not ACCESS_TOKEN:
        raise AgentError("HONEYPOT_ACCESS_TOKEN is required")

    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Accept": "application/json",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"

    request = Request(
        f"{SERVER_URL}{path}",
        data=body,
        method=method,
        headers=headers,
    )

    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise AgentError(f"{method} {path} failed: HTTP {exc.code} {detail}") from exc
    except URLError as exc:
        raise AgentError(f"{method} {path} failed: {exc.reason}") from exc


def command_for(node):
    node_type = str(node.get("honeypot_type", "")).lower()
    base = [
        sys.executable,
        str(HONEYZXC_PATH / "honeyzxc.py"),
        "--address",
        str(node.get("host") or "0.0.0.0"),
        "--port",
        str(node.get("port")),
        "--username",
        DEFAULT_USERNAME,
        "--password",
        DEFAULT_PASSWORD,
    ]

    if node_type in {"ssh", "ssh_honeypot"}:
        return base + ["--ssh"]
    if node_type in {"http", "web", "wordpress"}:
        return base + ["--http"]

    return None


def start_process(node):
    command = command_for(node)
    if not command:
        print(f"skip unsupported honeypot type: {node.get('honeypot_type')}")
        return None

    env = os.environ.copy()
    env["HONEYZXC_NODE_ID"] = str(node["node_id"])
    env["PYTHONUNBUFFERED"] = "1"

    print(f"starting {node['node_id']} on {node.get('host')}:{node.get('port')}")
    return subprocess.Popen(
        command,
        cwd=HONEYZXC_PATH,
        env=env,
    )


def stop_process(node_id, process):
    if process.poll() is not None:
        return

    print(f"stopping {node_id}")
    process.terminate()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()


def sync_processes(nodes, processes):
    desired = {
        node["node_id"]: node
        for node in nodes
        if node.get("status") == "running"
    }

    for node_id in list(processes):
        if node_id not in desired or processes[node_id].poll() is not None:
            stop_process(node_id, processes[node_id])
            del processes[node_id]

    for node_id, node in desired.items():
        if node_id not in processes:
            process = start_process(node)
            if process is not None:
                processes[node_id] = process


def read_new_lines(path, offset):
    if not path.exists():
        return offset, []

    with path.open("r", encoding="utf-8") as handle:
        handle.seek(offset)
        lines = handle.readlines()
        return handle.tell(), lines


def post_sessions(offsets):
    for source, path in LOG_FILES.items():
        offset = offsets.get(str(path), 0)
        next_offset, lines = read_new_lines(path, offset)
        offsets[str(path)] = next_offset

        for line in lines:
            if not line.strip():
                continue

            try:
                session = json.loads(line)
            except json.JSONDecodeError:
                print(f"skip invalid jsonl line from {path}")
                continue

            node_id = session.get("node_id") or os.getenv("HONEYZXC_NODE_ID")
            if not node_id:
                print("skip session without node_id")
                continue

            result = request_json(
                "/agent/sessions",
                method="POST",
                payload={
                    "node_id": node_id,
                    "source": f"{source}-honeyzxc",
                    "session": session,
                },
            )
            print(f"uploaded session {result.get('session_id')} stored={result.get('stored')}")


def main():
    processes = {}
    offsets = {}
    request_json("/agent/heartbeat", method="POST")
    print(f"agent connected to {SERVER_URL}")

    while True:
        try:
            response = request_json("/agent/honeypots")
            sync_processes(response.get("items", []), processes)
            post_sessions(offsets)
        except AgentError as exc:
            print(exc)

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()

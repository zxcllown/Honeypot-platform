import json
import re
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter


DB_PATH = Path(__file__).resolve().parents[2] / "data" / "telemetry.db"


def safe_json_loads(value, default):
    if not value:
        return default

    try:
        return json.loads(value)
    except Exception:
        return default


def extract_ip_ports(text: str) -> list[str]:
    return sorted(set(
        re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}:\d{2,5}\b", text)
    ))


def extract_urls(text: str) -> list[str]:
    urls = re.findall(r"https?://[^\s\"']+", text)
    cleaned = []

    for url in urls:
        url = url.rstrip(".,);]")
        if url.startswith("http://:") or url.startswith("https://:"):
            continue
        cleaned.append(url)

    return sorted(set(cleaned))


def normalize_syscall_name(line: str) -> str | None:
    line = line.strip()

    match = re.search(r"(execve|openat|connect|chmod|unlink|rename|mkdir|rmdir)\(", line)
    if match:
        return match.group(1)

    return None


def extract_exec_paths(syscalls: list[str]) -> list[str]:
    paths = []

    for line in syscalls:
        match = re.search(r'execve\("([^"]+)"', line)
        if match:
            paths.append(match.group(1))

    return sorted(set(paths))


def extract_opened_files(syscalls: list[str]) -> list[str]:
    files = []

    for line in syscalls:
        match = re.search(r'openat\(.*?, "([^"]+)"', line)
        if match:
            path = match.group(1)
            if path not in (".",):
                files.append(path)

    return sorted(set(files))


def extract_connect_targets(syscalls: list[str]) -> list[str]:
    targets = []

    for line in syscalls:
        ip_match = re.search(
            r'sin_addr=inet_addr\("([^"]+)"\).*?sin_port=htons\((\d+)\)',
            line
        )

        if ip_match:
            ip = ip_match.group(1)
            port = ip_match.group(2)
            targets.append(f"{ip}:{port}")

        unix_match = re.search(r'sun_path="([^"]+)"', line)
        if unix_match:
            targets.append(unix_match.group(1))

    return sorted(set(targets))


def summarize_syscalls(syscalls: list[str]) -> dict:
    counter = Counter()

    for line in syscalls:
        name = normalize_syscall_name(line)
        if name:
            counter[name] += 1

    return {
        "total": sum(counter.values()),
        "by_type": dict(counter),
        "exec_paths": extract_exec_paths(syscalls),
        "opened_files": extract_opened_files(syscalls),
        "connect_targets": extract_connect_targets(syscalls),
    }


def build_file_activity(row: sqlite3.Row, syscalls: list[str]) -> dict:
    files_created = safe_json_loads(row["files_created"], [])
    files_modified = safe_json_loads(row["files_modified"], [])
    files_deleted = safe_json_loads(row["files_deleted"], [])

    opened_files = extract_opened_files(syscalls)

    sensitive_files = []

    sensitive_patterns = [
        "/etc/passwd",
        "/etc/shadow",
        ".ssh",
        "id_rsa",
        "authorized_keys",
        "/etc/crontab",
        "/var/spool/cron",
        ".bashrc",
        ".profile",
    ]

    for path in opened_files + files_created + files_modified + files_deleted:
        if any(pattern in path for pattern in sensitive_patterns):
            sensitive_files.append(path)

    return {
        "created": sorted(set(files_created)),
        "modified": sorted(set(files_modified)),
        "deleted": sorted(set(files_deleted)),
        "opened": sorted(set(opened_files)),
        "sensitive_access": sorted(set(sensitive_files)),
    }


def build_process_activity(syscalls: list[str], command_results: list[dict]) -> dict:
    exec_paths = extract_exec_paths(syscalls)

    failed_commands = [
        item.get("command")
        for item in command_results
        if item.get("exit_code") not in (0, None)
    ]

    successful_commands = [
        item.get("command")
        for item in command_results
        if item.get("exit_code") == 0
    ]

    suspicious_processes = []

    suspicious_names = [
        "sh", "bash", "zsh", "python", "python3", "perl", "php",
        "nc", "ncat", "netcat", "socat", "wget", "curl", "sudo", "su"
    ]

    for path in exec_paths:
        base = path.split("/")[-1]
        if base in suspicious_names:
            suspicious_processes.append(path)

    return {
        "exec_paths": exec_paths,
        "suspicious_processes": sorted(set(suspicious_processes)),
        "failed_commands": [cmd for cmd in failed_commands if cmd],
        "successful_commands": [cmd for cmd in successful_commands if cmd],
    }


def build_network_activity(text: str, syscalls: list[str], network_connections: list[str]) -> dict:
    urls = extract_urls(text)
    ip_ports = extract_ip_ports(text)
    syscall_targets = extract_connect_targets(syscalls)

    dev_tcp = re.findall(r"/dev/tcp/[\w\.\-]+/\d+", text)

    return {
        "urls": sorted(set(urls)),
        "ip_ports": sorted(set(ip_ports)),
        "dev_tcp": sorted(set(dev_tcp)),
        "syscall_connect_targets": sorted(set(syscall_targets)),
        "network_indicators": sorted(set(network_connections + urls + ip_ports + dev_tcp + syscall_targets)),
    }


def detect_behaviors(
    text: str,
    commands: list[str],
    syscalls: list[str],
    file_activity: dict,
    process_activity: dict,
    network_activity: dict,
    exit_code: int | None,
) -> list[str]:
    behaviors = set()

    low = text.lower()
    commands_text = "\n".join(commands).lower()

    if "wget " in low or "curl " in low or any("wget " in c.lower() or "curl " in c.lower() for c in commands):
        behaviors.add("payload_download_attempt")

    if (
        "python3 -c" in low or "python -c" in low or
        "bash -c" in low or "sh -c" in low or
        "perl -e" in low or "php -r" in low
    ):
        behaviors.add("inline_script_execution")

    if (
        "/dev/tcp/" in low or
        "nc -e" in low or
        "ncat -e" in low or
        "netcat -e" in low or
        any("/dev/tcp/" in item for item in network_activity["network_indicators"])
    ):
        behaviors.add("reverse_shell_attempt")

    if (
        "temporary failure in name resolution" in low or
        "unable to resolve host address" in low or
        "network is unreachable" in low or
        "enetunreach" in low
    ):
        behaviors.add("network_blocked_by_sandbox")

    if exit_code not in (0, None):
        behaviors.add("execution_error_detected")

    if file_activity["created"] or file_activity["modified"] or file_activity["deleted"]:
        behaviors.add("filesystem_change_detected")

    if file_activity["sensitive_access"]:
        behaviors.add("sensitive_file_access")

    if any("connect(" in line for line in syscalls):
        behaviors.add("syscall_network_connect")

    if any("execve(" in line for line in syscalls):
        behaviors.add("process_spawn_detected")

    if any("chmod(" in line for line in syscalls):
        behaviors.add("permission_change_detected")

    if any("unlink(" in line or "rename(" in line for line in syscalls):
        behaviors.add("file_cleanup_or_rename_detected")

    if "sudo" in commands_text or "/usr/bin/sudo" in "\n".join(process_activity["exec_paths"]):
        behaviors.add("privilege_escalation_attempt")

    if "crontab" in commands_text or any("crontab" in f for f in file_activity["opened"]):
        behaviors.add("persistence_attempt")

    return sorted(behaviors)


def build_attack_chain(behaviors: list[str]) -> list[str]:
    chain = []

    if "sensitive_file_access" in behaviors or "process_spawn_detected" in behaviors:
        chain.append("Discovery")

    if "payload_download_attempt" in behaviors:
        chain.append("Payload Download")

    if "inline_script_execution" in behaviors or "process_spawn_detected" in behaviors:
        chain.append("Execution")

    if "reverse_shell_attempt" in behaviors or "syscall_network_connect" in behaviors:
        chain.append("Command and Control")

    if "privilege_escalation_attempt" in behaviors:
        chain.append("Privilege Escalation")

    if "persistence_attempt" in behaviors:
        chain.append("Persistence")

    if "file_cleanup_or_rename_detected" in behaviors:
        chain.append("Defense Evasion / Cleanup")

    return list(dict.fromkeys(chain))


def calculate_severity(behaviors: list[str]) -> float:
    weights = {
        "payload_download_attempt": 0.25,
        "inline_script_execution": 0.20,
        "reverse_shell_attempt": 0.40,
        "network_blocked_by_sandbox": 0.10,
        "execution_error_detected": 0.05,
        "filesystem_change_detected": 0.15,
        "sensitive_file_access": 0.20,
        "syscall_network_connect": 0.25,
        "process_spawn_detected": 0.10,
        "permission_change_detected": 0.20,
        "file_cleanup_or_rename_detected": 0.20,
        "privilege_escalation_attempt": 0.35,
        "persistence_attempt": 0.35,
    }

    score = sum(weights.get(behavior, 0.0) for behavior in behaviors)
    return round(min(score, 1.0), 2)


def build_summary(behaviors: list[str], attack_chain: list[str], network_activity: dict) -> str:
    parts = []

    if "reverse_shell_attempt" in behaviors:
        parts.append("Detected reverse shell behavior.")

    if "payload_download_attempt" in behaviors:
        parts.append("Detected payload download attempt.")

    if "privilege_escalation_attempt" in behaviors:
        parts.append("Detected privilege escalation attempt.")

    if "persistence_attempt" in behaviors:
        parts.append("Detected persistence-related activity.")

    if "sensitive_file_access" in behaviors:
        parts.append("Detected access to sensitive files.")

    if "network_blocked_by_sandbox" in behaviors:
        parts.append("Network activity was blocked by sandbox isolation.")

    if attack_chain:
        parts.append("Attack chain: " + " -> ".join(attack_chain) + ".")

    indicators = network_activity.get("network_indicators", [])
    if indicators:
        parts.append("Network indicators: " + ", ".join(indicators) + ".")

    if not parts:
        parts.append("No high-confidence sandbox behavior detected.")

    return " ".join(parts)


def analyze_sandbox_run(row: sqlite3.Row) -> dict:
    stdout = row["stdout"] or ""
    stderr = row["stderr"] or ""
    text = f"{stdout}\n{stderr}"

    network_connections = safe_json_loads(row["network_connections"], [])
    syscalls = safe_json_loads(row["syscalls"], [])
    commands = safe_json_loads(row["commands_executed"], [])
    command_results = safe_json_loads(row["command_results"], [])

    syscall_summary = summarize_syscalls(syscalls)
    file_activity = build_file_activity(row, syscalls)
    process_activity = build_process_activity(syscalls, command_results)
    network_activity = build_network_activity(text, syscalls, network_connections)

    behaviors = detect_behaviors(
        text=text,
        commands=commands,
        syscalls=syscalls,
        file_activity=file_activity,
        process_activity=process_activity,
        network_activity=network_activity,
        exit_code=row["exit_code"],
    )

    indicators = network_activity["network_indicators"]
    attack_chain = build_attack_chain(behaviors)
    severity_score = calculate_severity(behaviors)

    summary = build_summary(
        behaviors=behaviors,
        attack_chain=attack_chain,
        network_activity=network_activity,
    )

    return {
        "session_id": row["session_id"],
        "sandbox_run_id": row["id"],
        "behaviors": behaviors,
        "indicators": indicators,
        "severity_score": severity_score,
        "summary": summary,
        "syscall_summary": syscall_summary,
        "file_activity": file_activity,
        "process_activity": process_activity,
        "network_activity": network_activity,
        "attack_chain": attack_chain,
    }


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS telemetry_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            sandbox_run_id INTEGER NOT NULL,
            behaviors TEXT,
            indicators TEXT,
            severity_score REAL,
            summary TEXT,
            syscall_summary TEXT,
            file_activity TEXT,
            process_activity TEXT,
            network_activity TEXT,
            attack_chain TEXT,
            analyzed_at TEXT
        )
        """)
        conn.commit()


def save_analysis(analysis: dict):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        INSERT INTO telemetry_analysis (
            session_id,
            sandbox_run_id,
            behaviors,
            indicators,
            severity_score,
            summary,
            syscall_summary,
            file_activity,
            process_activity,
            network_activity,
            attack_chain,
            analyzed_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            analysis["session_id"],
            analysis["sandbox_run_id"],
            json.dumps(analysis["behaviors"], ensure_ascii=False),
            json.dumps(analysis["indicators"], ensure_ascii=False),
            analysis["severity_score"],
            analysis["summary"],
            json.dumps(analysis["syscall_summary"], ensure_ascii=False),
            json.dumps(analysis["file_activity"], ensure_ascii=False),
            json.dumps(analysis["process_activity"], ensure_ascii=False),
            json.dumps(analysis["network_activity"], ensure_ascii=False),
            json.dumps(analysis["attack_chain"], ensure_ascii=False),
            datetime.now(timezone.utc).isoformat(),
        ))
        conn.commit()


def analyze_all_unprocessed():
    init_db()

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""
        SELECT *
        FROM sandbox_runs
        WHERE id NOT IN (
            SELECT sandbox_run_id FROM telemetry_analysis
        )
        ORDER BY id ASC
        """)

        rows = cur.fetchall()

    for row in rows:
        analysis = analyze_sandbox_run(row)
        save_analysis(analysis)
        print(
            f"[telemetry_analyzer] analyzed "
            f"session={analysis['session_id']} "
            f"run={analysis['sandbox_run_id']} "
            f"score={analysis['severity_score']}"
        )


if __name__ == "__main__":
    analyze_all_unprocessed()
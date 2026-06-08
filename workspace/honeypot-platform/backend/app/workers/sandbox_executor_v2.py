import re
import subprocess
import time
import shlex
from datetime import datetime, timezone

from shared import (
    event_bus,
    Streams,
    RiskDecisionEvent,
    SandboxResultEvent,
    SandboxResult,
    CommandResult,
)


SANDBOX_IMAGE = "sandbox-image"
TIMEOUT_SECONDS = 30

# isolated | filesystem | syscall
SANDBOX_LEVEL = "syscall"

# Для syscall можно поставить False, если strace плохо работает под gVisor.
USE_GVISOR = False


def extract_network_indicators(text: str) -> list[str]:
    urls = re.findall(r"https?://[^\s\"']+", text)
    urls = [
        u.rstrip(".,);]")
        for u in urls
        if not u.startswith("http://:") and not u.startswith("https://:")
    ]

    ip_ports = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}:\d{2,5}\b", text)
    dev_tcp = re.findall(r"/dev/tcp/[\w\.\-]+/\d+", text)

    return sorted(set(urls + ip_ports + dev_tcp))


def extract_syscalls(text: str) -> list[str]:
    syscall_names = (
        "execve(",
        "openat(",
        "connect(",
        "chmod(",
        "unlink(",
        "rename(",
        "mkdir(",
        "rmdir(",
    )

    result = []

    for line in text.splitlines():
        line = line.strip()
        if any(name in line for name in syscall_names):
            result.append(line)

    return result


def parse_docker_diff(diff_output: str) -> tuple[list[str], list[str], list[str]]:
    created = []
    modified = []
    deleted = []

    for line in diff_output.splitlines():
        line = line.strip()
        if not line:
            continue

        status, _, path = line.partition(" ")

        if status == "A":
            created.append(path)
        elif status == "C":
            modified.append(path)
        elif status == "D":
            deleted.append(path)

    return created, modified, deleted


def build_script(commands: list[str]) -> str:
    lines = ["set +e", ""]

    for idx, cmd in enumerate(commands):
        clean_cmd = (cmd or "").strip()

        lines.append(f'echo "__CMD_START__:{idx}"')

        if clean_cmd == "exit":
            lines.append('echo "exit command skipped by sandbox"')
            lines.append(f'echo "__CMD_EXIT__:{idx}:0"')
            lines.append("")
            continue

        safe_cmd = shlex.quote(clean_cmd)

        if SANDBOX_LEVEL == "syscall":
            lines.append(
                "strace -f "
                "-e trace=execve,openat,connect,chmod,unlink,rename,mkdir,rmdir "
                f"bash -lc {safe_cmd}"
            )
        else:
            lines.append(f"bash -lc {safe_cmd}")

        lines.append(f'echo "__CMD_EXIT__:{idx}:$?"')
        lines.append("")

    return "\n".join(lines)


def parse_command_results(
    commands: list[str],
    stdout: str,
    stderr: str,
    total_duration_ms: int,
) -> list[CommandResult]:
    results = []
    duration_per_cmd = int(total_duration_ms / max(len(commands), 1))

    combined = stdout + "\n" + stderr

    for idx, cmd in enumerate(commands):
        start_marker = f"__CMD_START__:{idx}"
        exit_pattern = re.compile(rf"__CMD_EXIT__:{idx}:(\d+)")

        start_pos = combined.find(start_marker)

        if start_pos == -1:
            results.append(
                CommandResult(
                    command=cmd,
                    exit_code=0,
                    stdout="",
                    stderr="command marker not found",
                    duration_ms=duration_per_cmd,
                    network_indicators=extract_network_indicators(cmd),
                )
            )
            continue

        after_start = start_pos + len(start_marker)
        exit_match = exit_pattern.search(combined, after_start)

        if exit_match:
            exit_code = int(exit_match.group(1))
            end_pos = exit_match.start()
            command_output = combined[after_start:end_pos].strip()
        else:
            exit_code = 0
            command_output = combined[after_start:].strip()

        results.append(
            CommandResult(
                command=cmd,
                exit_code=exit_code,
                stdout=command_output,
                stderr="",
                duration_ms=duration_per_cmd,
                network_indicators=extract_network_indicators(command_output + "\n" + cmd),
            )
        )

    return results


def create_container(commands: list[str]) -> tuple[str, str]:
    create_cmd = ["docker", "create"]

    if USE_GVISOR:
        create_cmd.extend(["--runtime", "runsc"])

    create_cmd.extend([
        "--network", "none",
        "--memory", "256m",
        "--cpus", "0.5",
        "--pids-limit", "64",
        "--tmpfs", "/tmp:rw,size=64m",
        "--tmpfs", "/var/tmp:rw,size=64m",
        SANDBOX_IMAGE,
        "bash",
        "-lc",
        build_script(commands),
    ])

    created = subprocess.run(
        create_cmd,
        capture_output=True,
        text=True,
        timeout=10,
    )

    if created.returncode != 0:
        return "", created.stderr or created.stdout

    return created.stdout.strip(), ""


def run_session(commands: list[str]) -> dict:
    container_id = ""
    started_perf = time.perf_counter()

    try:
        container_id, create_error = create_container(commands)

        if not container_id:
            return {
                "exit_code": 125,
                "stdout": "",
                "stderr": create_error,
                "files_created": [],
                "files_modified": [],
                "files_deleted": [],
                "network_connections": extract_network_indicators(
                    create_error + "\n" + "\n".join(commands)
                ),
                "command_results": [],
                "commands_executed": commands,
                "syscalls": [],
            }

        start_result = subprocess.run(
            ["docker", "start", container_id],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if start_result.returncode != 0:
            return {
                "exit_code": start_result.returncode,
                "stdout": start_result.stdout,
                "stderr": start_result.stderr,
                "files_created": [],
                "files_modified": [],
                "files_deleted": [],
                "network_connections": extract_network_indicators(
                    start_result.stdout + "\n" + start_result.stderr + "\n" + "\n".join(commands)
                ),
                "command_results": [],
                "commands_executed": commands,
                "syscalls": [],
            }

        wait_result = subprocess.run(
            ["docker", "wait", container_id],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )

        logs_result = subprocess.run(
            ["docker", "logs", container_id],
            capture_output=True,
            text=True,
            timeout=10,
        )

        diff_result = subprocess.run(
            ["docker", "diff", container_id],
            capture_output=True,
            text=True,
            timeout=10,
        )

        files_created, files_modified, files_deleted = [], [], []

        if SANDBOX_LEVEL in ("filesystem", "syscall"):
            files_created, files_modified, files_deleted = parse_docker_diff(
                diff_result.stdout
            )

        duration_ms = int((time.perf_counter() - started_perf) * 1000)

        stdout = logs_result.stdout
        stderr = logs_result.stderr

        command_results = parse_command_results(
            commands=commands,
            stdout=stdout,
            stderr=stderr,
            total_duration_ms=duration_ms,
        )

        exit_code = 0

        for command_result in command_results:
            if command_result.exit_code != 0:
                exit_code = command_result.exit_code
                break

        if wait_result.returncode != 0:
            exit_code = wait_result.returncode

        network_connections = extract_network_indicators(
            stdout + "\n" + stderr + "\n" + "\n".join(commands)
        )

        syscalls = []

        if SANDBOX_LEVEL == "syscall":
            syscalls = extract_syscalls(stdout + "\n" + stderr)

        return {
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "files_created": files_created,
            "files_modified": files_modified,
            "files_deleted": files_deleted,
            "network_connections": network_connections,
            "command_results": command_results,
            "commands_executed": commands,
            "syscalls": syscalls,
        }

    except subprocess.TimeoutExpired:
        return {
            "exit_code": 124,
            "stdout": "",
            "stderr": f"Timeout: execution exceeded {TIMEOUT_SECONDS} seconds",
            "files_created": [],
            "files_modified": [],
            "files_deleted": [],
            "network_connections": extract_network_indicators("\n".join(commands)),
            "command_results": [],
            "commands_executed": commands,
            "syscalls": [],
        }

    finally:
        if container_id:
            subprocess.run(
                ["docker", "rm", "-f", container_id],
                capture_output=True,
                text=True,
            )


def run():
    while True:
        events = event_bus.consume(
            Streams.SANDBOX,
            "sandbox_executor",
            "sandbox_1",
        )

        for msg_id, data in events:
            try:
                risk_event = RiskDecisionEvent.model_validate(data)

                if not risk_event.decision.sandbox_required:
                    event_bus.ack(Streams.SANDBOX, "sandbox_executor", msg_id)
                    continue

                commands = risk_event.decision.commands_to_sandbox

                if not commands:
                    session = event_bus.get_session(risk_event.session_id)
                    commands = [c["cmd"] for c in session.get("commands", [])] if session else []

                if not commands:
                    event_bus.ack(Streams.SANDBOX, "sandbox_executor", msg_id)
                    continue

                result = run_session(commands)

                sandbox_result = SandboxResult(
                    session_id=risk_event.session_id,
                    exit_code=result["exit_code"],
                    sandbox_level=SANDBOX_LEVEL,
                    commands_executed=result["commands_executed"],
                    command_results=result["command_results"],
                    files_created=result["files_created"],
                    files_modified=result["files_modified"],
                    files_deleted=result["files_deleted"],
                    network_connections=result["network_connections"],
                    syscalls=result.get("syscalls", []),
                    stdout=result["stdout"],
                    stderr=result["stderr"],
                )

                result_event = SandboxResultEvent(
                    event_type="sandbox.executed",
                    correlation_id=risk_event.correlation_id,
                    session_id=risk_event.session_id,
                    result=sandbox_result,
                    executed_at=datetime.now(timezone.utc),
                )

                event_bus.publish(Streams.TELEMETRY, result_event)
                event_bus.ack(Streams.SANDBOX, "sandbox_executor", msg_id)

            except Exception as e:
                print(f"[sandbox_executor_v2] error: {e}")


if __name__ == "__main__":
    run()
import re
import subprocess
import time
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
TIMEOUT_SECONDS = 15

# isolated | filesystem | network | syscall
SANDBOX_LEVEL = "filesystem"

USE_GVISOR = True


def extract_network_indicators(text: str) -> list[str]:
    urls = re.findall(r"https?://[^\s\"']+", text)
    ip_ports = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}:\d{2,5}\b", text)
    dev_tcp = re.findall(r"/dev/tcp/[\w\.\-]+/\d+", text)

    return sorted(set(urls + ip_ports + dev_tcp))


def base_docker_args() -> list[str]:
    args = ["docker", "create"]

    if USE_GVISOR:
        args += ["--runtime=runsc"]

    args += [
        "--network", "none",
        "--memory", "256m",
        "--cpus", "0.5",
        "--pids-limit", "64",
        "--tmpfs", "/tmp:rw,size=64m",
        "--tmpfs", "/var/tmp:rw,size=64m",
        SANDBOX_IMAGE,
    ]

    return args


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


def docker_rm(container_id: str):
    if container_id:
        subprocess.run(
            ["docker", "rm", "-f", container_id],
            capture_output=True,
            text=True,
        )


def run_command_filesystem(cmd: str) -> dict:
    started = time.perf_counter()

    create_cmd = base_docker_args() + ["bash", "-lc", cmd]

    container_id = ""

    try:
        created = subprocess.run(
            create_cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if created.returncode != 0:
            return {
                "command": cmd,
                "exit_code": created.returncode,
                "stdout": created.stdout,
                "stderr": created.stderr,
                "duration_ms": int((time.perf_counter() - started) * 1000),
                "files_created": [],
                "files_modified": [],
                "files_deleted": [],
                "network_indicators": extract_network_indicators(created.stdout + "\n" + created.stderr + "\n" + cmd),
            }

        container_id = created.stdout.strip()

        subprocess.run(
            ["docker", "start", container_id],
            capture_output=True,
            text=True,
            timeout=5,
        )

        wait_result = subprocess.run(
            ["docker", "wait", container_id],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )

        exit_code = int(wait_result.stdout.strip() or "0")

        logs = subprocess.run(
            ["docker", "logs", container_id],
            capture_output=True,
            text=True,
            timeout=5,
        )

        diff = subprocess.run(
            ["docker", "diff", container_id],
            capture_output=True,
            text=True,
            timeout=5,
        )

        files_created, files_modified, files_deleted = parse_docker_diff(diff.stdout)

        stdout = logs.stdout
        stderr = logs.stderr

        return {
            "command": cmd,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "duration_ms": int((time.perf_counter() - started) * 1000),
            "files_created": files_created,
            "files_modified": files_modified,
            "files_deleted": files_deleted,
            "network_indicators": extract_network_indicators(stdout + "\n" + stderr + "\n" + cmd),
        }

    except subprocess.TimeoutExpired:
        return {
            "command": cmd,
            "exit_code": 124,
            "stdout": "",
            "stderr": f"Timeout: execution exceeded {TIMEOUT_SECONDS} seconds",
            "duration_ms": int((time.perf_counter() - started) * 1000),
            "files_created": [],
            "files_modified": [],
            "files_deleted": [],
            "network_indicators": extract_network_indicators(cmd),
        }

    finally:
        docker_rm(container_id)


def run_command_isolated(cmd: str) -> dict:
    started = time.perf_counter()

    docker_cmd = ["docker", "run", "--rm"]

    if USE_GVISOR:
        docker_cmd += ["--runtime=runsc"]

    docker_cmd += [
        "--network", "none",
        "--memory", "256m",
        "--cpus", "0.5",
        "--pids-limit", "64",
        "--tmpfs", "/tmp:rw,size=64m",
        "--tmpfs", "/var/tmp:rw,size=64m",
        SANDBOX_IMAGE,
        "bash", "-lc", cmd,
    ]

    try:
        proc = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )

        return {
            "command": cmd,
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "duration_ms": int((time.perf_counter() - started) * 1000),
            "files_created": [],
            "files_modified": [],
            "files_deleted": [],
            "network_indicators": extract_network_indicators(proc.stdout + "\n" + proc.stderr + "\n" + cmd),
        }

    except subprocess.TimeoutExpired:
        return {
            "command": cmd,
            "exit_code": 124,
            "stdout": "",
            "stderr": f"Timeout: execution exceeded {TIMEOUT_SECONDS} seconds",
            "duration_ms": int((time.perf_counter() - started) * 1000),
            "files_created": [],
            "files_modified": [],
            "files_deleted": [],
            "network_indicators": extract_network_indicators(cmd),
        }


def run_command_network(cmd: str) -> dict:
    # Пока network-level = network none + усиленный extraction.
    # Позже сюда добавим proxy/sinkhole.
    return run_command_filesystem(cmd)


def run_command_syscall(cmd: str) -> dict:
    # Пока placeholder.
    # На следующем этапе сюда добавим strace:
    # strace -f -e trace=execve,openat,connect,chmod,unlink bash -lc "<cmd>"
    return run_command_filesystem(cmd)


def run_single_command(cmd: str) -> dict:
    if SANDBOX_LEVEL == "isolated":
        return run_command_isolated(cmd)

    if SANDBOX_LEVEL == "filesystem":
        return run_command_filesystem(cmd)

    if SANDBOX_LEVEL == "network":
        return run_command_network(cmd)

    if SANDBOX_LEVEL == "syscall":
        return run_command_syscall(cmd)

    return run_command_filesystem(cmd)


def run_in_sandbox(commands: list[str]) -> dict:
    all_stdout = []
    all_stderr = []

    all_files_created = []
    all_files_modified = []
    all_files_deleted = []
    all_network = []

    command_results = []

    final_exit_code = 0

    for cmd in commands:
        result = run_single_command(cmd)

        all_stdout.append(f"$ {cmd}\n{result['stdout']}")
        all_stderr.append(f"$ {cmd}\n{result['stderr']}")

        all_files_created.extend(result["files_created"])
        all_files_modified.extend(result["files_modified"])
        all_files_deleted.extend(result["files_deleted"])
        all_network.extend(result["network_indicators"])

        command_results.append(
            CommandResult(
                command=cmd,
                exit_code=result["exit_code"],
                stdout=result["stdout"],
                stderr=result["stderr"],
                duration_ms=result["duration_ms"],
                network_indicators=result["network_indicators"],
            )
        )

        if result["exit_code"] != 0 and final_exit_code == 0:
            final_exit_code = result["exit_code"]

    return {
        "exit_code": final_exit_code,
        "stdout": "\n".join(all_stdout),
        "stderr": "\n".join(all_stderr),
        "files_created": sorted(set(all_files_created)),
        "files_modified": sorted(set(all_files_modified)),
        "files_deleted": sorted(set(all_files_deleted)),
        "network_connections": sorted(set(all_network)),
        "command_results": command_results,
        "commands_executed": commands,
    }


def run():
    while True:
        events = event_bus.consume(
            Streams.SANDBOX,
            "sandbox_executor",
            "sandbox_1",
        )

        for msg_id, data in events:
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

            result = run_in_sandbox(commands)

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
                syscalls=[],
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


if __name__ == "__main__":
    run()
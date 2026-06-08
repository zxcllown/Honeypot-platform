import shlex
from datetime import datetime, timezone

from shared import event_bus, Streams, ClassifiedEvent, RiskDecisionEvent, RiskDecision

WINDOW_BEFORE = 2
WINDOW_AFTER = 2


def build_sandbox_window(commands: list[str], command_classes: list[str]) -> list[str]:
    selected_indexes = set()

    for i, cmd_class in enumerate(command_classes):
        if cmd_class == "sandbox_execute":
            start = max(0, i - WINDOW_BEFORE)
            end = min(len(commands), i + WINDOW_AFTER + 1)

            for j in range(start, end):
                selected_indexes.add(j)

    return [commands[i] for i in sorted(selected_indexes)]

SANDBOX_COMMANDS = {
    "wget", "curl", "fetch", "sh", "bash", "python", "python3", "perl", "ruby", "php",
    "chmod", "chown", "tar", "unzip", "gunzip", "nc", "ncat", "netcat", "socat",
    "crontab", "systemctl", "service", "ssh", "scp", "docker", "podman",
    "base64"
}

OBSERVE_COMMANDS = {
    "id", "whoami", "groups", "uname", "hostname", "uptime", "ps", "top",
    "ifconfig", "ip", "netstat", "ss", "ls", "pwd", "find", "tree",
    "cat", "less", "more", "head", "tail", "grep", "awk", "sed",
    "last", "w", "dpkg", "rpm", "echo", "exit"
}

SUSPICIOUS_PATTERNS = [
    "wget ", "curl ", "chmod +x", "base64 -d",
    "python -c", "python3 -c", "perl -e", "php -r",
    "bash -c", "sh -c", "/dev/tcp/", "nc -e", "ncat -e",
    "| sh", "| bash", "&& sh", "&& bash"
]


def classify_command(cmd: str) -> str:
    cmd = (cmd or "").strip()
    if not cmd:
        return "safe_ignore"

    low = cmd.lower()

    for pattern in SUSPICIOUS_PATTERNS:
        if pattern in low:
            return "sandbox_execute"

    try:
        parts = shlex.split(cmd)
    except ValueError:
        parts = cmd.split()

    cmd_base = parts[0] if parts else ""

    if cmd_base.startswith("./") or cmd_base.endswith(".sh"):
        return "sandbox_execute"

    if cmd_base in SANDBOX_COMMANDS:
        return "sandbox_execute"

    if cmd_base in OBSERVE_COMMANDS:
        return "observe_only"

    return "safe_ignore"


def run():
    while True:
        events = event_bus.consume(Streams.CLASSIFIED, "risk_engine", "risk_1")

        for msg_id, data in events:
            classified = ClassifiedEvent.model_validate(data)
            clf = classified.classification
            session_id = classified.session_id

            session = event_bus.get_session(session_id)
            commands = [c.get("cmd", "") for c in session.get("commands", [])] if session else []

            observe_commands = []
            ignored_commands = []
            command_classes = []

            for cmd in commands:
                cmd_class = classify_command(cmd)
                command_classes.append(cmd_class)

                if cmd_class == "observe_only":
                    observe_commands.append(cmd)
                elif cmd_class == "safe_ignore":
                    ignored_commands.append(cmd)

            sandbox_commands = build_sandbox_window(commands, command_classes)

            sandbox_required = False
            reason = []

            if not session:
                reason.append("session_not_found")

            if not commands:
                reason.append("session_commands_not_found")

            if clf.classification == "malicious" and clf.confidence >= 0.7:
                reason.append("high_confidence_malicious")

            elif clf.classification == "mixed" and clf.confidence >= 0.6:
                reason.append("medium_confidence_mixed")

            if "Command and Control" in clf.tactics:
                reason.append("c2_detected")

            if "Execution" in clf.tactics:
                reason.append("execution_detected")

            if sandbox_commands:
                sandbox_required = True
                reason.append("sandbox_window_found")

            if not sandbox_commands and (
                "high_confidence_malicious" in reason
                or "medium_confidence_mixed" in reason
                or "c2_detected" in reason
                or "execution_detected" in reason
            ):
                reason.append("sandbox_skipped_no_executable_commands")

            decision = RiskDecision(
                session_id=session_id,
                risk_score=clf.confidence,
                sandbox_required=sandbox_required,
                reason=reason,
                commands_to_sandbox=sandbox_commands,
                observe_commands=observe_commands,
                ignored_commands=ignored_commands,
            )

            risk_event = RiskDecisionEvent(
                event_type="risk.decided",
                correlation_id=classified.correlation_id,
                session_id=session_id,
                decision=decision,
                decided_at=datetime.now(timezone.utc),
            )

            event_bus.publish(Streams.SANDBOX, risk_event)
            event_bus.ack(Streams.CLASSIFIED, "risk_engine", msg_id)


if __name__ == "__main__":
    run()
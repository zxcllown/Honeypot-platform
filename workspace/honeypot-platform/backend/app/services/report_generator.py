from report_builder import build_report


def _percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def _list_or_none(items: list[str]) -> str:
    if not items:
        return "- none"
    return "\n".join(f"- {item}" for item in items)


def generate_text_report(session_id: str) -> str:
    report = build_report(session_id)

    classification = report.get("classification", {})
    risk = report.get("risk", {})
    sandbox = report.get("sandbox", {})

    classification_type = classification.get("type", "unknown")
    confidence = classification.get("confidence", 0.0)
    tactics = classification.get("tactics", [])
    model = classification.get("model", "unknown")

    risk_score = risk.get("score", 0.0)
    sandbox_required = risk.get("sandbox_required", False)
    reasons = risk.get("reason", [])
    observe_commands = risk.get("observe_commands", [])
    commands_to_sandbox = risk.get("commands_to_sandbox", [])

    exit_code = sandbox.get("exit_code")
    network_connections = sandbox.get("network_connections", [])
    stdout = sandbox.get("stdout", "")
    stderr = sandbox.get("stderr", "")

    lines = []

    lines.append("=" * 60)
    lines.append("HONEYPOT SECURITY REPORT")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Session ID: {session_id}")
    lines.append("")
    lines.append("1. Classification")
    lines.append("-" * 60)
    lines.append(f"Result: {classification_type}")
    lines.append(f"Confidence: {_percent(confidence)}")
    lines.append(f"Model: {model}")
    lines.append("")
    lines.append("Detected tactics:")
    lines.append(_list_or_none(tactics))
    lines.append("")
    lines.append("2. Risk Decision")
    lines.append("-" * 60)
    lines.append(f"Risk score: {_percent(risk_score)}")
    lines.append(f"Sandbox required: {sandbox_required}")
    lines.append("")
    lines.append("Decision reasons:")
    lines.append(_list_or_none(reasons))
    lines.append("")
    lines.append("Observed commands:")
    lines.append(_list_or_none(observe_commands))
    lines.append("")
    lines.append("Commands selected for sandbox:")
    lines.append(_list_or_none(commands_to_sandbox))
    lines.append("")
    lines.append("3. Sandbox Execution")
    lines.append("-" * 60)

    if sandbox:
        lines.append(f"Exit code: {exit_code}")
        lines.append("")
        lines.append("Detected network indicators:")
        lines.append(_list_or_none(network_connections))
        lines.append("")
        lines.append("STDOUT:")
        lines.append(stdout.strip() if stdout.strip() else "- empty")
        lines.append("")
        lines.append("STDERR:")
        lines.append(stderr.strip() if stderr.strip() else "- empty")
    else:
        lines.append("Sandbox was not executed or no sandbox data was found.")

    lines.append("")
    lines.append("4. Summary")
    lines.append("-" * 60)

    if classification_type == "malicious":
        lines.append(
            f"The session was classified as malicious with "
            f"{_percent(confidence)} confidence."
        )
    else:
        lines.append(
            f"The session was classified as {classification_type} with "
            f"{_percent(confidence)} confidence."
        )

    if tactics:
        lines.append(
            "Detected attacker behavior matches the following tactics: "
            + ", ".join(tactics)
            + "."
        )

    if sandbox_required:
        lines.append(
            "Risk Engine decided to execute selected suspicious commands "
            "inside the sandbox."
        )

    if network_connections:
        lines.append(
            "The sandbox detected network-related indicators: "
            + ", ".join(network_connections)
            + "."
        )

    if "Temporary failure in name resolution" in stderr:
        lines.append(
            "Network access was blocked by sandbox isolation policy "
            "(network disabled), which prevented external communication."
        )

    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m app.services.report_generator <session_id>")
        raise SystemExit(1)

    print(generate_text_report("860e867d"))
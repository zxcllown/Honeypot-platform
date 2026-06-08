import json
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter


DATA_DIR = Path(__file__).resolve().parents[2] / "data"
NODES_DIR = DATA_DIR / "federated_nodes"
OUTPUT_PATH = DATA_DIR / "global_threat_view.json"


def safe_json_load(path: Path) -> dict | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[federated_aggregator] failed to load {path}: {e}")
        return None


def counter_from_pairs(pairs):
    counter = Counter()

    for item in pairs or []:
        if not isinstance(item, list | tuple) or len(item) != 2:
            continue

        key, value = item
        counter[key] += int(value)

    return counter


def load_node_summaries() -> list[dict]:
    NODES_DIR.mkdir(parents=True, exist_ok=True)

    summaries = []

    for path in sorted(NODES_DIR.glob("*.json")):
        summary = safe_json_load(path)
        if summary:
            summaries.append(summary)

    local_summary_path = DATA_DIR / "node_summary.json"
    if local_summary_path.exists():
        summary = safe_json_load(local_summary_path)
        if summary:
            summaries.append(summary)

    deduped = {}

    for summary in summaries:
        node_id = summary.get("node_id", "unknown-node")
        generated_at = summary.get("generated_at", "")

        if node_id not in deduped:
            deduped[node_id] = summary
        else:
            old_generated_at = deduped[node_id].get("generated_at", "")
            if generated_at > old_generated_at:
                deduped[node_id] = summary

    return list(deduped.values())


def build_global_view(summaries: list[dict]) -> dict:
    behavior_counter = Counter()
    indicator_counter = Counter()
    attack_chain_counter = Counter()

    recommendation_status_counter = Counter()
    recommendation_priority_counter = Counter()
    recommendation_action_counter = Counter()

    node_ids = []
    node_regions = Counter()

    total_sessions = 0
    total_recommendations = 0
    severity_values = []
    max_severity = 0.0

    for summary in summaries:
        node_id = summary.get("node_id", "unknown-node")
        node_region = summary.get("node_region", "unknown-region")

        node_ids.append(node_id)
        node_regions[node_region] += 1

        telemetry = summary.get("telemetry", {})
        adaptive = summary.get("adaptive", {})

        total_sessions += int(telemetry.get("sessions_analyzed", 0))
        total_recommendations += int(adaptive.get("recommendations_total", 0))

        avg_severity = float(telemetry.get("avg_severity", 0.0))
        node_sessions = int(telemetry.get("sessions_analyzed", 0))

        if node_sessions > 0:
            severity_values.extend([avg_severity] * node_sessions)

        max_severity = max(max_severity, float(telemetry.get("max_severity", 0.0)))

        behavior_counter.update(counter_from_pairs(telemetry.get("top_behaviors", [])))
        indicator_counter.update(counter_from_pairs(telemetry.get("top_indicators", [])))
        attack_chain_counter.update(counter_from_pairs(telemetry.get("top_attack_chains", [])))

        recommendation_status_counter.update(adaptive.get("by_status", {}))
        recommendation_priority_counter.update(adaptive.get("by_priority", {}))
        recommendation_action_counter.update(counter_from_pairs(adaptive.get("top_actions", [])))

    avg_global_severity = (
        round(sum(severity_values) / len(severity_values), 3)
        if severity_values else 0.0
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "privacy_mode": "aggregated_only_no_raw_logs",
        "nodes": {
            "count": len(summaries),
            "node_ids": node_ids,
            "regions": dict(node_regions),
        },
        "global_telemetry": {
            "sessions_analyzed": total_sessions,
            "avg_severity": avg_global_severity,
            "max_severity": max_severity,
            "top_behaviors": behavior_counter.most_common(20),
            "top_indicators": indicator_counter.most_common(20),
            "top_attack_chains": attack_chain_counter.most_common(20),
        },
        "global_adaptive": {
            "recommendations_total": total_recommendations,
            "by_status": dict(recommendation_status_counter),
            "by_priority": dict(recommendation_priority_counter),
            "top_actions": recommendation_action_counter.most_common(20),
        },
    }


def save_global_view(global_view: dict):
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(global_view, f, ensure_ascii=False, indent=2)

    print(f"[federated_aggregator] exported {OUTPUT_PATH}")
    print(json.dumps(global_view, ensure_ascii=False, indent=2))


def aggregate():
    summaries = load_node_summaries()

    if not summaries:
        print("[federated_aggregator] no node summaries found")
        return

    global_view = build_global_view(summaries)
    save_global_view(global_view)


if __name__ == "__main__":
    aggregate()
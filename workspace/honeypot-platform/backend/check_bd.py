import sqlite3

conn = sqlite3.connect("../backend/data/telemetry.db")
cur = conn.cursor()

for table in ["classified_sessions", "risk_decisions", "sandbox_runs", "telemetry_analysis", "adaptive_actions_log", "adaptive_recommendations"]:
    print("\n", table)
    cur.execute(f"SELECT * FROM {table}")
    for row in cur.fetchall():
        print(row)

conn.close()
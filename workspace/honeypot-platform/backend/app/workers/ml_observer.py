from shared import event_bus, Streams, SessionEvent, ClassifiedEvent, ClassificationResult
from ml_observer.classifier.ssh.predict import predict_session
from ml_observer.classifier.http.predict import predict_http_session
from datetime import datetime, timezone

def run():
    while True:
        events = event_bus.consume(Streams.EVENTS, "ml_observer", "ml_1")

        for msg_id, data in events:
            session_event = SessionEvent.model_validate(data)
            session = session_event.session
            session_id = session.get("session_id")
            if session_id:
                event_bus.save_session(session_id, session)

            # Классификация
            if session_event.source == "ssh-honeypot":
                commands = [c['cmd'] for c in session.get('commands', [])]
                result = predict_session(commands)
                model = "SessionSSHClassifier"
            elif session_event.source == "http-honeypot":
                requests = session.get('requests', [])
                result = predict_http_session(requests)
                model = "SessionHTTPClassifier"
            else:
                continue

            result_type = result.get("type", "unknown")
            result_conf = result.get("confidence", 0.0)

            if result_conf < 0.1:
                result_type = "benign"

            # Публикация результата с тем же correlation_id
            classified = ClassifiedEvent(
                event_type="session.classified",
                correlation_id=session_event.correlation_id,  # ← от SessionEvent
                session_id=session.get("session_id"),
                classification=ClassificationResult(
                    session_id=session.get("session_id"),
                    classification=result_type,
                    tactics=result.get("attack_types", []),
                    confidence=result_conf,
                    model_name = model
                ),
                classified_at=datetime.now(timezone.utc)
            )
            event_bus.publish(Streams.CLASSIFIED, classified)
            event_bus.ack(Streams.EVENTS, "ml_observer", msg_id)


if __name__ == "__main__":
    run()
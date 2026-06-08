import json
import redis
from .config import REDIS_HOST, REDIS_PORT, REDIS_DB
from .schemas import BaseEvent, Streams


class EventBus:
    def __init__(self):
        self._client = redis.Redis(
            host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB,
            decode_responses=True
        )

    def publish(self, stream: Streams, event: BaseEvent) -> str:
        data = event.model_dump(mode="json")
        self._client.xadd(str(stream), {"data": json.dumps(data, ensure_ascii=False)})
        return event.event_id

    def consume(self, stream: Streams, group: str, consumer: str,
                block_ms: int = 5000, count: int = 10):
        try:
            self._client.xgroup_create(str(stream), group, id='0', mkstream=True)
        except redis.ResponseError:
            pass

        events = self._client.xreadgroup(
            groupname=group,
            consumername=consumer,
            streams={str(stream): '>'},
            block=block_ms,
            count=count
        )

        result = []
        for _, messages in events:
            for msg_id, msg_data in messages:
                data = json.loads(msg_data['data'])
                result.append((msg_id, data))
        return result

    def ack(self, stream: Streams, group: str, event_id: str):
        self._client.xack(str(stream), group, event_id)

    # Session Store (Redis Hash)
    def save_session(self, session_id: str, session_data: dict, ttl_seconds: int = 86400):
        key = f"sessions:{session_id}"
        self._client.hset(key, mapping={"data": json.dumps(session_data, ensure_ascii=False)})
        self._client.expire(key, ttl_seconds)

    def get_session(self, session_id: str) -> dict | None:
        data = self._client.hget(f"sessions:{session_id}", "data")
        if data:
            return json.loads(data)
        return None

    def delete_session(self, session_id: str):
        self._client.delete(f"sessions:{session_id}")


event_bus = EventBus()
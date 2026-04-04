from threading import Lock


class JobRunnerRepository:
    def __init__(self) -> None:
        self._accepted: list[dict[str, object]] = []
        self._lock = Lock()

    def record_submission(self, payload: dict[str, object]) -> None:
        with self._lock:
            self._accepted.append(dict(payload))

    def list_submissions(self) -> list[dict[str, object]]:
        with self._lock:
            return [dict(item) for item in self._accepted]

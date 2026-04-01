import worker_training


def test_import() -> None:
    assert worker_training.__name__ == "worker_training"

import json

from playlist_bridge.state.checkpoint import CheckpointStore


def test_is_processed_false_for_unknown_key(tmp_path):
    store = CheckpointStore(tmp_path / "processed.json")
    assert store.is_processed("queen::bohemian rhapsody") is False


def test_mark_processed_marks_key_and_updates_len(tmp_path):
    store = CheckpointStore(tmp_path / "processed.json")
    store.mark_processed("queen::bohemian rhapsody")

    assert store.is_processed("queen::bohemian rhapsody") is True
    assert len(store) == 1


def test_mark_processed_is_idempotent_for_same_key(tmp_path):
    store = CheckpointStore(tmp_path / "processed.json", flush_every=5)
    store.mark_processed("a")
    store.mark_processed("a")
    store.mark_processed("a")

    assert len(store) == 1


def test_loads_existing_state_from_disk(tmp_path):
    path = tmp_path / "processed.json"
    path.write_text(json.dumps({"processed_keys": ["a", "b"]}))

    store = CheckpointStore(path)

    assert store.is_processed("a") is True
    assert store.is_processed("b") is True
    assert len(store) == 2


def test_flush_writes_current_state_to_disk(tmp_path):
    path = tmp_path / "processed.json"
    store = CheckpointStore(path, flush_every=100)
    store.mark_processed("a")
    store.flush()

    on_disk = json.loads(path.read_text())
    assert on_disk == {"processed_keys": ["a"]}


def test_mark_processed_flushes_incrementally_not_all_at_once(tmp_path):
    """Critical test: with flush_every=2, only the entries that reached the
    flush threshold are actually on disk before a later entry is added — the
    still-pending entry must not be there yet.
    """
    path = tmp_path / "processed.json"
    store = CheckpointStore(path, flush_every=2)

    store.mark_processed("k1")  # pending=1, below threshold, no flush yet
    store.mark_processed("k2")  # pending=2, reaches threshold, flush happens
    store.mark_processed("k3")  # pending=1 again, below threshold, no flush yet

    on_disk_store = CheckpointStore(path)
    assert on_disk_store.is_processed("k1") is True
    assert on_disk_store.is_processed("k2") is True
    assert on_disk_store.is_processed("k3") is False


def test_mark_processed_force_flush_writes_immediately(tmp_path):
    path = tmp_path / "processed.json"
    store = CheckpointStore(path, flush_every=100)

    store.mark_processed("k1", force_flush=True)

    on_disk_store = CheckpointStore(path)
    assert on_disk_store.is_processed("k1") is True


def test_corrupted_json_file_falls_back_to_empty_state(tmp_path):
    path = tmp_path / "processed.json"
    path.write_text("{not valid json")

    store = CheckpointStore(path)

    assert len(store) == 0
    assert store.is_processed("anything") is False

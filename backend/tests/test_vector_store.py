import pytest
from services.ai.rag.chunker import Chunk
from services.data.vector_store import ChromaVectorStore


def test_dimension_mismatch_does_not_wipe_other_datasets(tmp_path):
    """
    Regression test for P1 issue:
    ChromaDB collection wipeout on embedding dimension mismatch.

    Verifies that when Dataset A is stored with 3-dim vectors, an attempt to
    insert Dataset B with mismatched 2-dim vectors raises ValueError and DOES NOT
    wipe Dataset A's vectors from ChromaDB.
    """
    store = ChromaVectorStore(
        collection_name="test_wipeout_prevention",
        persist_directory=str(tmp_path / "chroma")
    )

    # 1. Add chunks for Dataset A (3-dimensional embeddings)
    chunk_a = Chunk(
        chunk_id="chunk_a_1",
        doc_id="doc_a",
        text="Sales data for Dataset A",
        metadata={"dataset_id": "dataset_A", "row_start": 0, "row_end": 1}
    )
    store.add_chunks([chunk_a], [[0.1, 0.2, 0.3]])

    assert store.count_vectors("dataset_A") == 1
    assert store.dataset_exists("dataset_A") is True

    # 2. Add chunks for Dataset B with mismatched dimension (2-dim instead of 3-dim)
    chunk_b = Chunk(
        chunk_id="chunk_b_1",
        doc_id="doc_b",
        text="Sales data for Dataset B",
        metadata={"dataset_id": "dataset_B", "row_start": 0, "row_end": 1}
    )

    # Must raise ValueError and NOT delete the collection
    with pytest.raises(ValueError) as exc_info:
        store.add_chunks([chunk_b], [[0.5, 0.6]])

    assert "Embedding dimension mismatch" in str(exc_info.value)

    # 3. Verify Dataset A's vectors are completely intact
    count_a_after = store.count_vectors("dataset_A")
    assert count_a_after == 1, (
        f"Regression detected: Dataset A vectors were lost! Expected 1, found {count_a_after}"
    )
    assert store.dataset_exists("dataset_A") is True

    # 4. Verify Dataset B has 0 vectors
    assert store.count_vectors("dataset_B") == 0


def test_dimension_reset_allowed_on_empty_collection(tmp_path):
    """
    Verifies that if a collection is completely empty (0 vectors),
    a dimension change safely resets the empty collection without error.
    """
    store = ChromaVectorStore(
        collection_name="test_empty_reset",
        persist_directory=str(tmp_path / "chroma_empty")
    )

    # 1. Add Dataset A with 3-dim vectors
    chunk_a = Chunk(
        chunk_id="chunk_a_1",
        doc_id="doc_a",
        text="Initial dataset",
        metadata={"dataset_id": "dataset_A"}
    )
    store.add_chunks([chunk_a], [[0.1, 0.2, 0.3]])
    assert store.count_vectors("dataset_A") == 1

    # 2. Delete Dataset A, leaving the collection completely empty (count == 0)
    store.delete_dataset("dataset_A")
    assert store.count_vectors("dataset_A") == 0

    # 3. Add Dataset B with 2-dim vectors on the now-empty collection
    chunk_b = Chunk(
        chunk_id="chunk_b_1",
        doc_id="doc_b",
        text="New dimensionality dataset",
        metadata={"dataset_id": "dataset_B"}
    )
    store.add_chunks([chunk_b], [[0.7, 0.8]])

    # Because collection had 0 vectors, it resets safely and stores Dataset B
    assert store.count_vectors("dataset_B") == 1
    assert store.dataset_exists("dataset_B") is True


def test_normal_multi_dataset_isolation_and_delete(tmp_path):
    """
    Verifies standard multi-dataset isolation, counting, and individual dataset deletion.
    """
    store = ChromaVectorStore(
        collection_name="test_isolation",
        persist_directory=str(tmp_path / "chroma_iso")
    )

    chunk_a1 = Chunk(chunk_id="a1", doc_id="da", text="Text A1", metadata={"dataset_id": "ds_a"})
    chunk_a2 = Chunk(chunk_id="a2", doc_id="da", text="Text A2", metadata={"dataset_id": "ds_a"})
    chunk_b1 = Chunk(chunk_id="b1", doc_id="db", text="Text B1", metadata={"dataset_id": "ds_b"})

    store.add_chunks([chunk_a1, chunk_a2], [[0.1, 0.2], [0.3, 0.4]])
    store.add_chunks([chunk_b1], [[0.5, 0.6]])

    assert store.count_vectors("ds_a") == 2
    assert store.count_vectors("ds_b") == 1

    # Delete only dataset A
    deleted = store.delete_dataset("ds_a")
    assert deleted is True

    # Dataset A vectors are gone, dataset B vectors remain
    assert store.count_vectors("ds_a") == 0
    assert store.dataset_exists("ds_a") is False
    assert store.count_vectors("ds_b") == 1
    assert store.dataset_exists("ds_b") is True


def test_dimension_mismatch_fails_closed_when_count_fails(tmp_path, monkeypatch):
    """
    Regression test for fail-closed hardening:
    Simulates `self.collection.count()` raising an exception when dimension
    mismatch recovery is triggered.

    Verifies that:
    1. delete_collection() is NEVER called.
    2. Existing vectors belonging to Dataset A remain intact and retrievable.
    3. The operation fails safely with a meaningful ValueError explaining that
       count could not be verified and destructive recovery was refused.
    4. The original exception is preserved as the __cause__.
    """
    from unittest.mock import MagicMock

    store = ChromaVectorStore(
        collection_name="test_fail_closed",
        persist_directory=str(tmp_path / "chroma_fail_closed")
    )

    # 1. Store Dataset A with 3-dim vectors
    chunk_a = Chunk(
        chunk_id="chunk_a_1",
        doc_id="doc_a",
        text="Sales data for Dataset A",
        metadata={"dataset_id": "dataset_A"}
    )
    store.add_chunks([chunk_a], [[0.1, 0.2, 0.3]])
    assert store.count_vectors("dataset_A") == 1

    # 2. Spy on delete_collection
    delete_mock = MagicMock(wraps=store.client.delete_collection)
    monkeypatch.setattr(store.client, "delete_collection", delete_mock)

    # 3. Simulate self.collection.count() raising an error during recovery
    original_count = store.collection.count

    def failing_count():
        raise RuntimeError("ChromaDB lock or disk I/O error during count")

    monkeypatch.setattr(store.collection, "count", failing_count)

    # 4. Attempt to add Dataset B with 2-dim vectors
    chunk_b = Chunk(
        chunk_id="chunk_b_1",
        doc_id="doc_b",
        text="Mismatched vector for Dataset B",
        metadata={"dataset_id": "dataset_B"}
    )

    with pytest.raises(ValueError) as exc_info:
        store.add_chunks([chunk_b], [[0.5, 0.6]])

    # 5. Verify exception messaging and that count failure is preserved as __cause__
    err_msg = str(exc_info.value)
    assert "collection count could not be verified" in err_msg
    assert "Destructive recovery was refused to prevent data loss" in err_msg
    assert exc_info.value.__cause__ is not None
    assert isinstance(exc_info.value.__cause__, RuntimeError)
    assert "ChromaDB lock or disk I/O error during count" in str(exc_info.value.__cause__)

    # 6. Verify delete_collection was NEVER called
    delete_mock.assert_not_called()

    # 7. Restore count and verify Dataset A vectors are still intact and searchable
    monkeypatch.setattr(store.collection, "count", original_count)
    assert store.count_vectors("dataset_A") == 1
    assert store.dataset_exists("dataset_A") is True

    search_res = store.search(query_embedding=[0.1, 0.2, 0.3], dataset_id="dataset_A", top_k=1)
    assert len(search_res) == 1
    assert search_res[0]["document"] == "Sales data for Dataset A"


def test_concurrent_ingestion_lock_prevents_race_on_dimension_reset(tmp_path):
    """
    Regression test for concurrency safety:
    Verifies that simultaneous ingestions across worker threads are serialized by
    the store's internal lock, preventing race conditions where an empty collection
    reset in one thread could delete vectors concurrently inserted by another thread.
    """
    import threading

    store = ChromaVectorStore(
        collection_name="test_concurrent_race",
        persist_directory=str(tmp_path / "chroma_concurrent")
    )

    barrier = threading.Barrier(2)
    results = {}
    errors = []

    def task_a():
        try:
            # Synchronize thread start at barrier to ensure simultaneous contention
            barrier.wait(timeout=5)
            chunk_a = Chunk(
                chunk_id="ca_1",
                doc_id="da",
                text="Dataset A record",
                metadata={"dataset_id": "ds_a"}
            )
            store.add_chunks([chunk_a], [[0.1, 0.2, 0.3]])
            results["thread_a_done"] = True
        except ValueError as ex:
            if "dimension" in str(ex).lower():
                results["thread_a_mismatch"] = True
            else:
                errors.append(f"Task A unexpected ValueError: {ex}")
        except Exception as ex:
            errors.append(f"Task A unexpected error: {ex}")

    def task_b():
        try:
            # Synchronize thread start at barrier to ensure simultaneous contention
            barrier.wait(timeout=5)
            chunk_b = Chunk(
                chunk_id="cb_1",
                doc_id="db",
                text="Dataset B record",
                metadata={"dataset_id": "ds_b"}
            )
            store.add_chunks([chunk_b], [[0.5, 0.6]])
            results["thread_b_done"] = True
        except ValueError as ex:
            if "dimension" in str(ex).lower():
                results["thread_b_mismatch"] = True
            else:
                errors.append(f"Task B unexpected ValueError: {ex}")
        except Exception as ex:
            errors.append(f"Task B unexpected exception: {ex}")

    t1 = threading.Thread(target=task_a)
    t2 = threading.Thread(target=task_b)

    t1.start()
    t2.start()

    t1.join(timeout=5)
    t2.join(timeout=5)

    assert not errors, f"Unexpected thread errors occurred: {errors}"
    # Verify that data preservation succeeded under concurrency:
    # Exactly one thread succeeds in establishing collection dimensions and inserting its chunk,
    # and the other thread is serialized, blocked by _lock, encounters dimension mismatch, and refuses to wipe.
    total_vectors = store.collection.count()
    assert total_vectors == 1, f"Expected 1 vector preserved under concurrent execution, found {total_vectors}"

    if results.get("thread_a_done"):
        assert results.get("thread_b_mismatch") is True, "Thread B should have failed with dimension mismatch"
        assert store.count_vectors("ds_a") == 1
        assert store.count_vectors("ds_b") == 0
    else:
        assert results.get("thread_b_done") is True, "Thread B should have succeeded if Thread A did not"
        assert results.get("thread_a_mismatch") is True, "Thread A should have failed with dimension mismatch"
        assert store.count_vectors("ds_b") == 1
        assert store.count_vectors("ds_a") == 0

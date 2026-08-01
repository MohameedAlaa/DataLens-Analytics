"""Unit tests for file upload, validation, CSV parsing, and upload limits."""

import io
import pytest
import pandas as pd


def test_upload_valid_csv(client, make_csv):
    """Test successful upload of a valid CSV file."""
    csv_bytes = make_csv("id,name,val\n1,Alpha,10.5\n2,Beta,20.0")
    files = {"file": ("test.csv", csv_bytes, "text/csv")}

    response = client.post("/upload", files=files)
    assert response.status_code == 200

    data = response.json()
    assert "dataset_id" in data
    assert data["filename"] == "test.csv"
    assert data["shape"] == [2, 3]
    assert data["columns"] == ["id", "name", "val"]
    assert len(data["preview"]) == 2


def test_upload_valid_excel(client):
    """Test successful upload of a valid Excel (.xlsx) file."""
    df = pd.DataFrame({"colA": [1, 2], "colB": ["x", "y"]})
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    excel_bytes = out.getvalue()

    files = {
        "file": (
            "test.xlsx",
            excel_bytes,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }

    response = client.post("/upload", files=files)
    assert response.status_code == 200

    data = response.json()
    assert "dataset_id" in data
    assert data["filename"] == "test.xlsx"
    assert data["shape"] == [2, 2]


def test_upload_missing_filename(client):
    """Test upload request with missing filename."""
    files = {"file": ("", b"data", "text/csv")}
    response = client.post("/upload", files=files)
    assert response.status_code in (400, 422)


def test_upload_invalid_extension(client):
    """Test upload request with unsupported extension (.txt)."""
    files = {"file": ("test.txt", b"some text content", "text/plain")}
    response = client.post("/upload", files=files)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data or "error" in data


def test_upload_empty_file_0bytes(client):
    """Test uploading an empty file (0 bytes)."""
    files = {"file": ("empty.csv", b"", "text/csv")}
    response = client.post("/upload", files=files)
    assert response.status_code == 400
    data = response.json()
    assert "empty" in str(data).lower()


def test_upload_empty_csv_no_rows(client):
    """Test uploading a CSV with header only and 0 data rows."""
    files = {"file": ("norows.csv", b"col1,col2\n", "text/csv")}
    response = client.post("/upload", files=files)
    assert response.status_code == 400
    data = response.json()
    assert "no data rows" in str(data).lower() or "empty" in str(data).lower()


def test_upload_duplicate_columns(client):
    """Test uploading a CSV containing duplicate column names."""
    csv_bytes = b"colA,colB,colA\n1,2,3\n4,5,6"
    files = {"file": ("dups.csv", csv_bytes, "text/csv")}
    response = client.post("/upload", files=files)
    assert response.status_code == 400
    assert "duplicate" in str(response.json()).lower()


def test_upload_magic_bytes_blocked_binary(client):
    """Test uploading an executable / binary file spoofed with a .csv extension."""
    # PE Header magic bytes: MZ\x90\x00...
    fake_exe = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"
    files = {"file": ("malicious.csv", fake_exe, "text/csv")}
    response = client.post("/upload", files=files)
    assert response.status_code == 400
    assert "binary" in str(response.json()).lower() or "executable" in str(response.json()).lower()


def test_upload_file_size_exceeded(client, monkeypatch):
    """Test file size limit validation (e.g. 413 error when exceeding max allowed bytes)."""
    from config import settings

    # Set temporary small max upload limit for testing (e.g. 50 bytes)
    monkeypatch.setattr(settings, "max_upload_bytes", 50)

    large_csv = b"col1,col2,col3\n" + b"a,b,c\n" * 10
    files = {"file": ("large.csv", large_csv, "text/csv")}

    response = client.post("/upload", files=files)
    assert response.status_code == 413
    assert "exceeds maximum" in str(response.json()).lower()

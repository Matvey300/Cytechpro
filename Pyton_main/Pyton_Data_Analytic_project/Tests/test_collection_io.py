import re
from pathlib import Path

import core.collection_io as collection_io
import pandas as pd


class DummySession:
    def __init__(self):
        self.collection_id = None
        self.collection_path = None
        self.df_asin = None


def test_make_dirname_and_parse():
    last_snapshot = "20250903"
    collection_id = "headphones_us"
    created_date = "20250820"
    dirname = collection_io.make_collection_dirname(last_snapshot, collection_id, created_date)
    parsed = collection_io.parse_collection_dirname(dirname)
    assert parsed["snap"] == last_snapshot
    assert parsed["cid"] == collection_id
    assert parsed["created"] == created_date


def test_create_collection_creates_new_style_folder_and_collection_csv(tmp_path: Path):
    # redirect collections root to a temp dir
    collection_io.COLLECTIONS_DIR = tmp_path
    session = DummySession()
    name = "headphones us"
    session = collection_io.create_collection(session, name=name)
    # The directory should exist
    assert session.collection_path.exists()
    # The directory name matches the new style regex
    assert re.match(collection_io._NEW_DIR_RE, session.collection_path.name)
    # collection.csv exists inside
    coll_csv = collection_io.collection_csv(session.collection_path)
    assert coll_csv.exists()
    # No legacy files present
    legacy_file1 = session.collection_path / f"{session.collection_id}_ASIN.csv"
    legacy_file2 = session.collection_path / f"{session.collection_id}__reviews.csv"
    assert not legacy_file1.exists()
    assert not legacy_file2.exists()
    # DataFrame is empty with expected columns
    df = pd.read_csv(coll_csv)
    expected_cols = ["asin", "title", "rating", "review_count", "country", "category_path"]
    assert list(df.columns) == expected_cols
    assert df.empty


def test_list_collections_sorts_new_style_by_snapshot_desc(tmp_path: Path):
    collection_io.COLLECTIONS_DIR = tmp_path

    # Create new-style folders with collection.csv
    folders = [
        ("20250903", "A_collection", "20250820"),
        ("20250901", "B_collection", "20250819"),
        ("20250820", "C_collection", "20250818"),
    ]
    for snap, cid, created in folders:
        d = collection_io.collection_dir(tmp_path, snap, cid, created)
        d.mkdir(parents=True)
        collection_io.collection_csv(d).write_text(
            "asin,title,rating,review_count,country,category_path\n"
        )

    result = collection_io.list_collections()
    # New style names sorted by snap desc
    expected_new_style = [
        f"{folders[0][0]}_{folders[0][1]}_created{folders[0][2]}",
        f"{folders[1][0]}_{folders[1][1]}_created{folders[1][2]}",
        f"{folders[2][0]}_{folders[2][1]}_created{folders[2][2]}",
    ]
    assert result == expected_new_style


def test_save_collection_writes_collection_csv(tmp_path: Path):
    collection_io.COLLECTIONS_DIR = tmp_path
    session = DummySession()
    session = collection_io.create_collection(session, name="test save")
    df = session.df_asin.copy()
    # Add one row using concat (append is deprecated)
    new_row = pd.DataFrame(
        [
            {
                "asin": "B000123",
                "title": "Test Product",
                "rating": 4.5,
                "review_count": 10,
                "country": "US",
                "category_path": "Electronics",
            }
        ]
    )
    if df.empty:
        df = new_row.copy()
    else:
        df = pd.concat([df, new_row], ignore_index=True)
    collection_io.save_collection(session, session.collection_id, df)
    coll_csv = collection_io.collection_csv(session.collection_path)
    df2 = pd.read_csv(coll_csv)
    assert len(df2) == 1
    assert session.collection_path.exists()
    # DataFrame saved into session matches what we wrote
    assert list(df2.columns) == list(df.columns)


# Additional tests for load_collection new-only support
def test_load_collection_only_new_format_success(tmp_path: Path):
    import core.collection_io as cio

    cio.COLLECTIONS_DIR = tmp_path
    # create two new-style folders for same cid; loader should pick newest snap
    cid = "cidA"
    d1 = cio.collection_dir(tmp_path, "20250901", cid, "20250820")
    d2 = cio.collection_dir(tmp_path, "20250903", cid, "20250820")
    d1.mkdir(parents=True)
    d2.mkdir(parents=True)
    (cio.collection_csv(d1)).write_text("asin,title\nA1,T1\n")
    (cio.collection_csv(d2)).write_text("asin,title\nA2,T2\n")

    class S:
        pass

    s = S()
    cio.load_collection(cid, s)
    assert s.collection_id == cid
    assert s.collection_path == d2
    assert list(s.df_asin.columns) == ["asin", "title"]


def test_load_collection_legacy_not_supported(tmp_path: Path):
    import core.collection_io as cio

    cio.COLLECTIONS_DIR = tmp_path
    # legacy folder with <cid>_ASIN.csv should NOT load
    cid = "legacyX"
    legacy = tmp_path / cid
    legacy.mkdir()
    (legacy / f"{cid}_ASIN.csv").write_text("asin,title\nX1,T\n")

    class S:
        pass

    s = S()
    import pytest

    with pytest.raises(FileNotFoundError):
        cio.load_collection(cid, s)

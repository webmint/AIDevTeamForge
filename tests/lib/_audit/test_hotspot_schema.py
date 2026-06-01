"""Tests for src/devforge/lib/_audit/hotspot_schema.py.

Coverage:
  Happy-path construction of FileScore and HotspotResult.
  JSON round-trip: build -> asdict -> json.dumps -> json.loads -> reconstruct.
  Every __post_init__ validation branch (one rejecting test per raise).
  Edge cases: zero churn/callers/size_loc accepted; empty top/next_candidates.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

import pytest

_LIB_DIR = Path(__file__).resolve().parents[3] / "src" / "devforge" / "lib"
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _audit import hotspot_schema  # noqa: E402
from _audit.hotspot_schema import FileScore, HotspotResult, SCHEMA_VERSION  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_file_score(**overrides):
    """Return a valid FileScore, overriding any fields."""
    defaults = dict(
        file="src/foo.py",
        churn=10,
        callers=5,
        size_loc=200,
        churn_norm=0.5,
        callers_norm=0.4,
        size_norm=0.3,
        score=0.46,
        rank=1,
    )
    defaults.update(overrides)
    return FileScore(**defaults)


def make_hotspot_result(**overrides):
    """Return a valid HotspotResult, overriding any fields."""
    defaults = dict(
        schema_version=SCHEMA_VERSION,
        weights={"c": 0.5, "k": 0.4, "s": 0.1},
        top=[make_file_score(rank=1)],
        next_candidates=[make_file_score(rank=2, file="src/bar.py")],
        total_files_scored=50,
    )
    defaults.update(overrides)
    return HotspotResult(**defaults)


def reconstruct_file_score(d):
    """Reconstruct FileScore from a plain dict (after asdict + json round-trip)."""
    return FileScore(**d)


def reconstruct_hotspot_result(d):
    """Reconstruct HotspotResult from a plain dict (after asdict + json round-trip)."""
    d = dict(d)
    d["top"] = [reconstruct_file_score(x) for x in d["top"]]
    d["next_candidates"] = [reconstruct_file_score(x) for x in d["next_candidates"]]
    return HotspotResult(**d)


# ---------------------------------------------------------------------------
# Happy-path construction
# ---------------------------------------------------------------------------

class TestFileScoreHappyPath:
    def test_basic_construction(self):
        fs = make_file_score()
        assert fs.file == "src/foo.py"
        assert fs.churn == 10
        assert fs.callers == 5
        assert fs.size_loc == 200
        assert fs.churn_norm == 0.5
        assert fs.callers_norm == 0.4
        assert fs.size_norm == 0.3
        assert fs.score == 0.46
        assert fs.rank == 1

    def test_zero_counts_accepted(self):
        fs = make_file_score(churn=0, callers=0, size_loc=0)
        assert fs.churn == 0
        assert fs.callers == 0
        assert fs.size_loc == 0

    def test_norm_boundary_zero(self):
        fs = make_file_score(churn_norm=0.0, callers_norm=0.0, size_norm=0.0, score=0.0)
        assert fs.score == 0.0

    def test_norm_boundary_one(self):
        fs = make_file_score(churn_norm=1.0, callers_norm=1.0, size_norm=1.0, score=1.0)
        assert fs.score == 1.0

    def test_rank_one(self):
        fs = make_file_score(rank=1)
        assert fs.rank == 1

    def test_rank_large(self):
        fs = make_file_score(rank=100)
        assert fs.rank == 100

    def test_int_norm_accepted(self):
        # int in [0,1] is acceptable (0 and 1 are valid)
        fs = make_file_score(churn_norm=0, callers_norm=1, size_norm=0, score=0)
        assert fs.churn_norm == 0


class TestHotspotResultHappyPath:
    def test_basic_construction(self):
        hr = make_hotspot_result()
        assert hr.schema_version == SCHEMA_VERSION
        assert hr.weights == {"c": 0.5, "k": 0.4, "s": 0.1}
        assert len(hr.top) == 1
        assert len(hr.next_candidates) == 1
        assert hr.total_files_scored == 50

    def test_empty_top_and_next_candidates(self):
        hr = make_hotspot_result(top=[], next_candidates=[])
        assert hr.top == []
        assert hr.next_candidates == []

    def test_zero_total_files_scored(self):
        hr = make_hotspot_result(total_files_scored=0)
        assert hr.total_files_scored == 0

    def test_multiple_top_entries(self):
        top = [make_file_score(rank=i + 1, file="src/f{0}.py".format(i)) for i in range(5)]
        hr = make_hotspot_result(top=top)
        assert len(hr.top) == 5


# ---------------------------------------------------------------------------
# JSON round-trip
# ---------------------------------------------------------------------------

class TestFileScoreRoundTrip:
    def test_round_trip(self):
        original = make_file_score()
        d = dataclasses.asdict(original)
        serialized = json.dumps(d)
        loaded = json.loads(serialized)
        reconstructed = reconstruct_file_score(loaded)
        assert reconstructed == original


class TestHotspotResultRoundTrip:
    def test_round_trip_with_items(self):
        original = make_hotspot_result()
        d = dataclasses.asdict(original)
        serialized = json.dumps(d)
        loaded = json.loads(serialized)
        reconstructed = reconstruct_hotspot_result(loaded)
        assert reconstructed == original

    def test_round_trip_empty_lists(self):
        original = make_hotspot_result(top=[], next_candidates=[])
        d = dataclasses.asdict(original)
        serialized = json.dumps(d)
        loaded = json.loads(serialized)
        reconstructed = reconstruct_hotspot_result(loaded)
        assert reconstructed == original


# ---------------------------------------------------------------------------
# FileScore validation failures
# ---------------------------------------------------------------------------

class TestFileScoreValidation:
    def test_empty_file_raises(self):
        with pytest.raises(ValueError, match="FileScore.file"):
            make_file_score(file="")

    def test_whitespace_only_file_raises(self):
        with pytest.raises(ValueError, match="FileScore.file"):
            make_file_score(file="   ")

    def test_non_string_file_raises(self):
        with pytest.raises(ValueError, match="FileScore.file"):
            make_file_score(file=123)

    def test_bool_churn_raises(self):
        with pytest.raises(ValueError, match="FileScore.churn"):
            make_file_score(churn=True)

    def test_negative_churn_raises(self):
        with pytest.raises(ValueError, match="FileScore.churn"):
            make_file_score(churn=-1)

    def test_non_int_churn_raises(self):
        with pytest.raises(ValueError, match="FileScore.churn"):
            make_file_score(churn=1.5)

    def test_bool_callers_raises(self):
        with pytest.raises(ValueError, match="FileScore.callers"):
            make_file_score(callers=False)

    def test_negative_callers_raises(self):
        with pytest.raises(ValueError, match="FileScore.callers"):
            make_file_score(callers=-1)

    def test_bool_size_loc_raises(self):
        with pytest.raises(ValueError, match="FileScore.size_loc"):
            make_file_score(size_loc=True)

    def test_negative_size_loc_raises(self):
        with pytest.raises(ValueError, match="FileScore.size_loc"):
            make_file_score(size_loc=-1)

    def test_churn_norm_above_one_raises(self):
        with pytest.raises(ValueError, match="FileScore.churn_norm"):
            make_file_score(churn_norm=1.1)

    def test_churn_norm_below_zero_raises(self):
        with pytest.raises(ValueError, match="FileScore.churn_norm"):
            make_file_score(churn_norm=-0.01)

    def test_callers_norm_out_of_range_raises(self):
        with pytest.raises(ValueError, match="FileScore.callers_norm"):
            make_file_score(callers_norm=2.0)

    def test_size_norm_out_of_range_raises(self):
        with pytest.raises(ValueError, match="FileScore.size_norm"):
            make_file_score(size_norm=-0.5)

    def test_score_above_one_raises(self):
        with pytest.raises(ValueError, match="FileScore.score"):
            make_file_score(score=1.5)

    def test_score_below_zero_raises(self):
        with pytest.raises(ValueError, match="FileScore.score"):
            make_file_score(score=-0.1)

    def test_bool_norm_raises(self):
        with pytest.raises(ValueError, match="FileScore.churn_norm"):
            make_file_score(churn_norm=True)

    def test_rank_zero_raises(self):
        with pytest.raises(ValueError, match="FileScore.rank"):
            make_file_score(rank=0)

    def test_rank_negative_raises(self):
        with pytest.raises(ValueError, match="FileScore.rank"):
            make_file_score(rank=-5)

    def test_bool_rank_raises(self):
        with pytest.raises(ValueError, match="FileScore.rank"):
            make_file_score(rank=True)


# ---------------------------------------------------------------------------
# HotspotResult validation failures
# ---------------------------------------------------------------------------

class TestHotspotResultValidation:
    def test_wrong_schema_version_raises(self):
        with pytest.raises(ValueError, match="schema_version"):
            make_hotspot_result(schema_version="99")

    def test_empty_schema_version_raises(self):
        with pytest.raises(ValueError, match="schema_version"):
            make_hotspot_result(schema_version="")

    def test_non_dict_weights_raises(self):
        with pytest.raises(ValueError, match="weights"):
            make_hotspot_result(weights=[0.5, 0.4, 0.1])

    def test_weights_missing_key_raises(self):
        with pytest.raises(ValueError, match="weights"):
            make_hotspot_result(weights={"c": 0.5, "k": 0.4})  # missing "s"

    def test_weights_extra_key_raises(self):
        with pytest.raises(ValueError, match="weights"):
            make_hotspot_result(weights={"c": 0.5, "k": 0.4, "s": 0.1, "x": 0.0})

    def test_weights_value_out_of_range_raises(self):
        with pytest.raises(ValueError, match="weights"):
            make_hotspot_result(weights={"c": 1.5, "k": 0.4, "s": 0.1})

    def test_weights_bool_value_raises(self):
        with pytest.raises(ValueError, match="weights"):
            make_hotspot_result(weights={"c": True, "k": 0.4, "s": 0.1})

    def test_top_not_list_raises(self):
        with pytest.raises(ValueError, match="top"):
            make_hotspot_result(top="not-a-list")

    def test_top_wrong_element_type_raises(self):
        with pytest.raises(ValueError, match="top"):
            make_hotspot_result(top=[123])

    def test_next_candidates_not_list_raises(self):
        with pytest.raises(ValueError, match="next_candidates"):
            make_hotspot_result(next_candidates="not-a-list")

    def test_next_candidates_wrong_element_type_raises(self):
        with pytest.raises(ValueError, match="next_candidates"):
            make_hotspot_result(next_candidates=["not-a-filescore"])

    def test_bool_total_files_scored_raises(self):
        with pytest.raises(ValueError, match="total_files_scored"):
            make_hotspot_result(total_files_scored=True)

    def test_negative_total_files_scored_raises(self):
        with pytest.raises(ValueError, match="total_files_scored"):
            make_hotspot_result(total_files_scored=-1)

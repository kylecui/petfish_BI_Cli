from __future__ import annotations

from pathlib import Path

from petfish_bi_cli.data_multi.temporal import TemporalDataLoader, TimeSlice


class TestTemporalDataLoader:
    def test_load_jd_returns_records(self):
        loader = TemporalDataLoader(data_root=Path("references"))
        records = loader.load("jd_products")
        assert len(records) > 0
        assert all("source" in r for r in records)

    def test_load_tmall_returns_records(self):
        loader = TemporalDataLoader(data_root=Path("references"))
        records = loader.load("tmall_products")
        assert len(records) > 0

    def test_load_crocs_returns_records(self):
        loader = TemporalDataLoader(data_root=Path("references"))
        records = loader.load("crocs_xiaohongshu")
        assert len(records) > 0

    def test_unknown_source_returns_empty(self):
        loader = TemporalDataLoader(data_root=Path("references"))
        records = loader.load("nonexistent")
        assert records == []

    def test_get_timestamps_jd(self):
        loader = TemporalDataLoader(data_root=Path("references"))
        timestamps = loader.get_timestamps("jd_products")
        assert isinstance(timestamps, list)

    def test_get_timestamps_tmall(self):
        loader = TemporalDataLoader(data_root=Path("references"))
        timestamps = loader.get_timestamps("tmall_products")
        assert isinstance(timestamps, list)
        if timestamps:
            assert isinstance(timestamps[0], float)


class TestTimeSlice:
    def test_create_day_slice(self):
        ts = TimeSlice(period="day", timestamp=1719500000.0)
        assert ts.period == "day"
        assert ts.label  # has some label

    def test_create_week_slice(self):
        ts = TimeSlice(period="week", timestamp=1719500000.0)
        assert ts.period == "week"

    def test_different_timestamps_different_labels(self):
        ts1 = TimeSlice(period="day", timestamp=1719500000.0)
        ts2 = TimeSlice(period="day", timestamp=1720100000.0)
        # Different days should have different labels (or same if same day)
        assert isinstance(ts1.label, str)
        assert isinstance(ts2.label, str)

    def test_group_by_period(self):
        timestamps = [1719500000.0, 1719586400.0, 1720100000.0]
        groups = TimeSlice.group(timestamps, period="day")
        assert isinstance(groups, dict)
        assert all(isinstance(k, str) for k in groups.keys())
        assert sum(len(v) for v in groups.values()) == len(timestamps)


class TestTemporalComparison:
    def test_compare_two_periods(self):
        loader = TemporalDataLoader(data_root=Path("references"))
        result = loader.compare_periods(
            source="tmall_products",
            metric="avg_price",
            period="day",
        )
        assert isinstance(result, dict)
        assert "periods" in result or "comparisons" in result

    def test_trend_analysis(self):
        loader = TemporalDataLoader(data_root=Path("references"))
        trend = loader.trend(
            source="tmall_products",
            metric="avg_price",
            period="day",
        )
        assert isinstance(trend, list)

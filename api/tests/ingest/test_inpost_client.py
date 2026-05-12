"""Unit tests for inpost_client filter logic."""

from __future__ import annotations

from typing import Any

from paczkomat_atlas_api.ingest.inpost_client import (
    is_locker_type,
    is_valid_point,
)


def _base_item(**overrides: Any) -> dict[str, Any]:
    item: dict[str, Any] = {
        "name": "WAW001",
        "country": "PL",
        "status": "Operating",
        "type": ["parcel_locker"],
        "address_details": {"province": "mazowieckie"},
        "location": {"latitude": 52.1, "longitude": 21.0},
    }
    item.update(overrides)
    return item


# ============ is_valid_point ============

class TestIsValidPoint:
    def test_accepts_normal_record(self) -> None:
        assert is_valid_point(_base_item()) is True

    def test_rejects_province_test_lowercase(self) -> None:
        assert is_valid_point(_base_item(address_details={"province": "test"})) is False

    def test_rejects_province_test_uppercase(self) -> None:
        assert is_valid_point(_base_item(address_details={"province": "TEST"})) is False

    def test_rejects_italian_dgm_test_uppercase(self) -> None:
        assert is_valid_point(_base_item(name="DGMTESTMODULAR")) is False

    def test_rejects_italian_dgm_test_lowercase(self) -> None:
        assert is_valid_point(_base_item(name="dgmtestnewfm")) is False

    def test_rejects_italian_dgm_test_with_suffix(self) -> None:
        assert is_valid_point(_base_item(name="DGMTEST_FOO123")) is False

    def test_accepts_dgm_prefix_without_test(self) -> None:
        """DGM is a real prefix used in PL for some lockers."""
        assert is_valid_point(_base_item(name="DGM001M")) is True

    def test_rejects_null_island_int(self) -> None:
        assert is_valid_point(_base_item(location={"latitude": 0, "longitude": 0})) is False

    def test_rejects_null_island_float(self) -> None:
        assert is_valid_point(_base_item(location={"latitude": 0.0, "longitude": 0.0})) is False

    def test_accepts_partial_zero_coords(self) -> None:
        """A real locker at lat=21 longitude=0 is not null island (both must be 0)."""
        assert is_valid_point(_base_item(location={"latitude": 21.0, "longitude": 0})) is True

    def test_rejects_unknown_status(self) -> None:
        assert is_valid_point(_base_item(status="Mystery")) is False

    def test_rejects_nonoperating_status(self) -> None:
        """NonOperating excluded per Phase 0 recon decision."""
        assert is_valid_point(_base_item(status="NonOperating")) is False

    def test_accepts_overloaded_status(self) -> None:
        """Overloaded = full but still operational (FR-common)."""
        assert is_valid_point(_base_item(status="Overloaded")) is True

    def test_accepts_disabled_status(self) -> None:
        assert is_valid_point(_base_item(status="Disabled")) is True

    def test_accepts_created_status(self) -> None:
        assert is_valid_point(_base_item(status="Created")) is True

    def test_handles_missing_address_details(self) -> None:
        item = _base_item()
        item.pop("address_details")
        assert is_valid_point(item) is True

    def test_handles_missing_location(self) -> None:
        item = _base_item()
        item.pop("location")
        # No location → no null island check trigger, but defensively this is invalid
        # Implementation currently allows; document behavior:
        assert is_valid_point(item) is True  # caller must check location separately


# ============ is_locker_type ============

class TestIsLockerType:
    def test_parcel_locker_only(self) -> None:
        assert is_locker_type(_base_item()) is True

    def test_pop_pudo(self) -> None:
        assert is_locker_type(_base_item(type=["pop"])) is False

    def test_pok_pudo(self) -> None:
        assert is_locker_type(_base_item(type=["pok"])) is False

    def test_missing_type(self) -> None:
        item = _base_item()
        item.pop("type")
        assert is_locker_type(item) is False

    def test_empty_type_list(self) -> None:
        assert is_locker_type(_base_item(type=[])) is False

    def test_mixed_parcel_locker_and_refrigerated(self) -> None:
        """Recon found one PL record with both — still a locker."""
        assert is_locker_type(_base_item(type=["parcel_locker", "refrigerated_locker_machine"])) is True

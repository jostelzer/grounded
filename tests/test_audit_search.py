import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "skills" / "grounded"
sys.path.insert(0, str(ROOT / "scripts"))

import audit_search  # noqa: E402


def record(angle, query, lane="general", **overrides):
    value = {
        "angle": angle,
        "angle_id": angle,
        "requested_query_or_seed": query,
        "lane": lane,
        "method": "keyword",
        "citation_direction": None,
        "completed": True,
        "status": "ok",
        "pages": 1,
    }
    value.update(overrides)
    return value


class SearchAuditTests(unittest.TestCase):
    def large_manifest(self):
        lanes = ["reviews", "primary", "foundational", "recent", "contrary-null"]
        records = []
        for angle in range(8):
            for query in range(3):
                records.append(record(
                    f"angle-{angle}", f"query {angle} {query}", lanes[angle % len(lanes)]
                ))
        for seed in range(5):
            for direction in ("backward", "forward"):
                records.append(record(
                    "angle-0", f"Seed{seed}", method=f"{direction}-citation",
                    citation_direction=direction, lane="citation-chase",
                ))
        return {"schema_version": 1, "records": records}

    def test_complete_large_funnel_passes(self):
        result = audit_search.audit_search(self.large_manifest(), size="large")
        self.assertEqual(result["status"], "pass", result["errors"])
        self.assertEqual(result["metrics"]["both_direction_central_papers"], 5)

    def test_failed_calls_do_not_satisfy_queries_or_chases(self):
        manifest = self.large_manifest()
        for item in manifest["records"]:
            if item["requested_query_or_seed"] in {"query 0 2", "Seed0"}:
                item["completed"] = False
                item["status"] = "rate limited"
                item["pages"] = 0
        result = audit_search.audit_search(manifest, size="large")
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("angle-0" in error for error in result["errors"]))
        self.assertTrue(any("central papers" in error for error in result["errors"]))

    def test_structured_saturation_override_is_auditable(self):
        manifest = self.large_manifest()
        manifest["records"] = [
            item for item in manifest["records"]
            if item["requested_query_or_seed"] != "query 0 2"
        ]
        override = {
            "reason": "The small field saturated across every available index.",
            "saturation_evidence": ["all eligible records repeated"],
            "allowed_search_shortfalls": ["queries"],
        }
        result = audit_search.audit_search(
            manifest, size="large", thin_literature_override=override
        )
        self.assertEqual(result["status"], "pass", result["errors"])
        self.assertTrue(any("override" in warning for warning in result["warnings"]))


class MaximaAreAdvisoryTests(unittest.TestCase):
    """Over-searching is over-diligence: minima stay hard errors, maxima
    warn. Zero-accept and superseded queries never count toward a maximum."""

    def small_manifest(self, extra=()):
        records = [
            record(f"angle-{n}", f"query {n} {q}", accepted=3)
            for n in range(3) for q in range(2)
        ]
        records.extend(extra)
        return {"schema_version": 1, "records": records}

    def test_small_within_bounds_passes_clean(self):
        result = audit_search.audit_search(self.small_manifest(), size="small")
        self.assertEqual(result["status"], "pass", result["errors"])
        self.assertEqual(result["warnings"], [])

    def test_extra_productive_query_warns_instead_of_failing(self):
        extra = [record("angle-0", "query 0 extra", accepted=4)]
        result = audit_search.audit_search(self.small_manifest(extra), size="small")
        self.assertEqual(result["status"], "pass", result["errors"])
        self.assertTrue(any("angle-0" in w for w in result["warnings"]))

    def test_zero_accept_query_does_not_count_toward_maximum(self):
        extra = [record("angle-0", "query 0 empty", accepted=0)]
        result = audit_search.audit_search(self.small_manifest(extra), size="small")
        self.assertEqual(result["status"], "pass", result["errors"])
        self.assertEqual(result["warnings"], [])

    def test_zero_accept_query_still_counts_toward_minimum(self):
        records = [
            record("angle-0", "query 0 empty", accepted=0),
        ] + [
            record(f"angle-{n}", f"query {n} 0", accepted=3) for n in range(1, 3)
        ]
        result = audit_search.audit_search(
            {"schema_version": 1, "records": records}, size="small"
        )
        self.assertEqual(result["status"], "pass", result["errors"])

    def test_superseded_records_are_excluded_from_coverage(self):
        extra = [record(
            "angle-0", "query 0 extra", accepted=4,
            superseded=True, superseded_reason="duplicate of the reviews query",
        )]
        result = audit_search.audit_search(self.small_manifest(extra), size="small")
        self.assertEqual(result["status"], "pass", result["errors"])
        self.assertEqual(result["warnings"], [])
        self.assertEqual(result["metrics"]["superseded_records"], 1)

    def test_too_many_angles_warns_instead_of_failing(self):
        records = [
            record(f"angle-{n}", f"query {n}", accepted=2) for n in range(6)
        ]
        result = audit_search.audit_search(
            {"schema_version": 1, "records": records}, size="small"
        )
        self.assertEqual(result["status"], "pass", result["errors"])
        self.assertTrue(any("at most" in w for w in result["warnings"]))

    def test_below_minimum_is_still_a_hard_error(self):
        records = [record("angle-0", "query 0", accepted=2)]
        result = audit_search.audit_search(
            {"schema_version": 1, "records": records}, size="small"
        )
        self.assertEqual(result["status"], "fail")


if __name__ == "__main__":
    unittest.main()

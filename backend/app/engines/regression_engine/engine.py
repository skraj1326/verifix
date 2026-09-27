"""Regression Intelligence Engine - Test prioritization and optimization."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TestResult:
    name: str
    status: str = "unknown"  # passed, failed, error, timeout
    runtime_seconds: float = 0.0
    coverage_delta: float = 0.0
    bugs_found: int = 0
    failure_count: int = 0
    is_flaky: bool = False
    affected_modules: list = field(default_factory=list)
    tags: list = field(default_factory=list)


class RegressionEngine:
    """Intelligent regression management.

    Features:
    - Rank tests by bug-finding potential
    - Detect redundant tests
    - Detect flaky tests
    - Identify tests affected by RTL changes
    - Recommend minimal regression sets
    - Prioritize tests targeting recent changes
    """

    def __init__(self):
        self.test_history: dict[str, list[TestResult]] = {}

    def rank_tests(self, results: list[TestResult]) -> list[dict]:
        """Rank tests by bug-finding potential and coverage improvement."""
        rankings = []
        for result in results:
            score = self._compute_priority_score(result)
            rankings.append({
                "test_name": result.name,
                "priority_score": score,
                "status": result.status,
                "runtime": result.runtime_seconds,
                "coverage_delta": result.coverage_delta,
                "reasons": self._explain_ranking(result),
            })

        rankings.sort(key=lambda x: x["priority_score"], reverse=True)
        return rankings

    def detect_flaky_tests(self, results: list[TestResult],
                           min_runs: int = 3) -> list[dict]:
        """Detect tests that intermittently pass/fail."""
        flaky = []
        for name, history in self.test_history.items():
            if len(history) < min_runs:
                continue

            recent = history[-min_runs:]
            statuses = [r.status for r in recent]

            passed = statuses.count("passed")
            failed = statuses.count("failed")

            if passed > 0 and failed > 0:
                flaky_rate = min(passed, failed) / len(statuses)
                flaky.append({
                    "test_name": name,
                    "flaky_rate": flaky_rate,
                    "recent_statuses": statuses,
                    "recommendation": (
                        "Investigate test environment stability"
                        if flaky_rate < 0.3 else
                        "Consider rewriting test with deterministic stimulus"
                    ),
                })

        return flaky

    def detect_redundant_tests(self, results: list[TestResult]) -> list[dict]:
        """Find tests that always produce the same result as another test."""
        redundant = []

        # Group by coverage delta
        coverage_groups: dict[float, list] = {}
        for r in results:
            # Round to 2 decimal places for grouping
            key = round(r.coverage_delta, 2)
            if key not in coverage_groups:
                coverage_groups[key] = []
            coverage_groups[key].append(r)

        for delta, group in coverage_groups.items():
            if len(group) > 1 and delta == 0.0:
                # Tests with zero coverage delta may be redundant
                for test in group[1:]:
                    redundant.append({
                        "test_name": test.name,
                        "potentially_redundant_with": group[0].name,
                        "reason": "Zero coverage delta, similar runtime",
                        "recommendation": "Consider removing or merging",
                    })

        return redundant

    def identify_affected_tests(self, changed_modules: list[str],
                                results: list[TestResult]) -> list[dict]:
        """Identify tests likely affected by RTL changes."""
        affected = []
        for result in results:
            overlap = set(result.affected_modules) & set(changed_modules)
            if overlap:
                affected.append({
                    "test_name": result.name,
                    "affected_modules": list(overlap),
                    "priority": "high" if result.status == "failed" else "medium",
                })

        affected.sort(key=lambda x: 0 if x["priority"] == "high" else 1)
        return affected

    def recommend_minimal_regression(self, results: list[TestResult],
                                     budget_minutes: float = 60.0) -> list[dict]:
        """Recommend a minimal test set that maximizes coverage within time budget."""
        ranked = self.rank_tests(results)
        selected = []
        total_time = 0.0

        for test in ranked:
            runtime = test["runtime"]
            if total_time + runtime <= budget_minutes:
                selected.append(test)
                total_time += runtime

        return {
            "selected_tests": selected,
            "total_tests": len(selected),
            "total_runtime_minutes": total_time,
            "budget_minutes": budget_minutes,
            "coverage_achieved": sum(t["coverage_delta"] for t in selected),
        }

    def compute_regression_summary(self, results: list[TestResult]) -> dict:
        """Compute overall regression summary."""
        total = len(results)
        passed = sum(1 for r in results if r.status == "passed")
        failed = sum(1 for r in results if r.status == "failed")
        errors = sum(1 for r in results if r.status == "error")
        timeouts = sum(1 for r in results if r.status == "timeout")

        total_time = sum(r.runtime_seconds for r in results)
        total_coverage = sum(r.coverage_delta for r in results)

        return {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "timeouts": timeouts,
            "pass_rate": (passed / total * 100) if total > 0 else 0,
            "total_runtime_seconds": total_time,
            "total_runtime_minutes": total_time / 60,
            "total_coverage_delta": total_coverage,
            "avg_runtime_per_test": total_time / total if total > 0 else 0,
        }

    def _compute_priority_score(self, result: TestResult) -> float:
        """Compute a priority score for a test."""
        score = 0.0

        # Failed tests are highest priority
        if result.status == "failed":
            score += 100
        elif result.status == "error":
            score += 80
        elif result.status == "timeout":
            score += 60

        # Coverage improvement
        score += result.coverage_delta * 10

        # Bug finding
        score += result.bugs_found * 50

        # Faster tests get slight priority
        if result.runtime_seconds > 0:
            score += max(0, 10 - result.runtime_seconds / 10)

        # Flaky tests get deprioritized
        if result.is_flaky:
            score -= 20

        return score

    def _explain_ranking(self, result: TestResult) -> list[str]:
        """Explain why a test was ranked at its position."""
        reasons = []
        if result.status == "failed":
            reasons.append("Test is failing")
        if result.coverage_delta > 0:
            reasons.append(f"Coverage delta: +{result.coverage_delta:.1f}%")
        if result.bugs_found > 0:
            reasons.append(f"Found {result.bugs_found} bug(s)")
        if result.runtime_seconds < 5:
            reasons.append("Fast execution")
        if result.is_flaky:
            reasons.append("Flaky test - investigate")
        return reasons

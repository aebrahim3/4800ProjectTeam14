#!/usr/bin/env python3
import argparse
import json
import socket
import sys
import time
import urllib.error
import urllib.request


DEFAULT_URL = "http://localhost:8004/career/course-recommendations"
DEFAULT_HEALTH_URL = "http://localhost:8004/health"
EXPECTED_MODEL_VERSION = "hybrid_nn_v1"


CASES = [
    {
        "name": "AWS Python Agile",
        "body": {
            "user_id": 1,
            "skill_gaps": ["AWS", "Python", "Agile"],
            "preferred_location": "British Columbia",
            "limit": 3,
        },
        "expected_status": 200,
    },
    {
        "name": "Python only",
        "body": {
            "user_id": 1,
            "skill_gaps": ["Python"],
            "preferred_location": "British Columbia",
            "limit": 5,
        },
        "expected_status": 200,
    },
    {
        "name": "AWS only",
        "body": {
            "user_id": 1,
            "skill_gaps": ["AWS"],
            "preferred_location": "British Columbia",
            "limit": 5,
        },
        "expected_status": 200,
    },
    {
        "name": "Kubernetes AWS",
        "body": {
            "user_id": 1,
            "skill_gaps": ["Kubernetes", "AWS"],
            "preferred_location": "British Columbia",
            "limit": 3,
        },
        "expected_status": 200,
    },
    {
        "name": "Unknown AWS",
        "body": {
            "user_id": 1,
            "skill_gaps": ["TotallyMadeUpSkillXYZ", "AWS"],
            "preferred_location": "British Columbia",
            "limit": 3,
        },
        "expected_status": 200,
        "expected_unknown": ["TotallyMadeUpSkillXYZ"],
    },
    {
        "name": "Empty skill gaps",
        "body": {
            "user_id": 1,
            "skill_gaps": [],
            "preferred_location": "British Columbia",
            "limit": 3,
        },
        "expected_status": 422,
    },
]


def read_json_response(response):
    payload = response.read().decode("utf-8")
    return json.loads(payload) if payload else {}


def get_json(url, timeout):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.status, read_json_response(response)


def post_json(url, body, timeout):
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, read_json_response(response)
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8")
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            data = {"raw": payload}
        return exc.code, data


def retry_request(operation, attempts, delay):
    last_exc = None
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except (ConnectionError, OSError, socket.timeout, urllib.error.URLError) as exc:
            last_exc = exc
            if attempt == attempts:
                break
            time.sleep(delay)
    raise last_exc


def wait_for_health(url, timeout, attempts, delay):
    for attempt in range(1, attempts + 1):
        try:
            status, data = get_json(url, timeout)
            if status == 200:
                print(f"Health check passed: {data}")
                return
        except Exception as exc:
            if attempt == attempts:
                raise RuntimeError(f"Service did not become healthy at {url}: {exc}") from exc
        time.sleep(delay)
    raise RuntimeError(f"Service did not become healthy at {url}")


def assert_recommendation_payload(case, status, data):
    expected_status = case["expected_status"]
    if status != expected_status:
        raise AssertionError(f"Expected HTTP {expected_status}, got {status}: {data}")

    if expected_status == 422:
        if "detail" not in data:
            raise AssertionError(f"Expected validation detail, got: {data}")
        return

    if data.get("model_version") != EXPECTED_MODEL_VERSION:
        raise AssertionError(f"Expected {EXPECTED_MODEL_VERSION}, got {data.get('model_version')}")
    if data.get("used_rule_fallback") is not False:
        raise AssertionError(f"Expected used_rule_fallback=false, got: {data.get('used_rule_fallback')}")

    expected_unknown = case.get("expected_unknown")
    if expected_unknown is not None and data.get("unknown_skill_gaps") != expected_unknown:
        raise AssertionError(f"Expected unknown skills {expected_unknown}, got {data.get('unknown_skill_gaps')}")

    recommendations = data.get("recommendations")
    if not recommendations:
        raise AssertionError("Expected at least one recommendation")

    required_fields = {
        "score",
        "dense_similarity",
        "skill_hit_count",
        "matched_skills",
        "missing_skills",
        "ranking_signals",
    }
    for recommendation in recommendations:
        missing_fields = required_fields - set(recommendation)
        if missing_fields:
            raise AssertionError(f"Recommendation missing fields {sorted(missing_fields)}: {recommendation}")
        score = recommendation["score"]
        if not isinstance(score, (int, float)) or not 0 <= score <= 1:
            raise AssertionError(f"Expected score in 0..1, got {score}")
        signals = recommendation["ranking_signals"]
        for key in (
            "dense_similarity_weight",
            "skill_coverage_weight",
            "is_local_weight",
            "credit_score_weight",
            "zero_hit_penalty_applied",
        ):
            if key not in signals:
                raise AssertionError(f"ranking_signals missing {key}: {signals}")


def print_case_summary(case, status, data):
    print(f"\n== {case['name']} ==")
    print(f"status: {status}")
    if status == 422:
        print(f"detail: {data.get('detail')}")
        return

    print(
        "model:",
        data.get("model_version"),
        "fallback:",
        data.get("used_rule_fallback"),
        "unknown:",
        data.get("unknown_skill_gaps"),
    )
    for recommendation in data.get("recommendations", []):
        print(
            recommendation.get("course_code"),
            recommendation.get("score"),
            "hits:",
            recommendation.get("matched_skills"),
            "missing:",
            recommendation.get("missing_skills"),
            "penalty:",
            recommendation.get("ranking_signals", {}).get("zero_hit_penalty_applied"),
        )


def main():
    parser = argparse.ArgumentParser(description="Smoke test the course recommendation API.")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--health-url", default=DEFAULT_HEALTH_URL)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--attempts", type=int, default=6)
    parser.add_argument("--retry-delay", type=float, default=3.0)
    parser.add_argument("--skip-health", action="store_true")
    args = parser.parse_args()

    if not args.skip_health:
        wait_for_health(args.health_url, args.timeout, args.attempts, args.retry_delay)

    failures = []
    for case in CASES:
        try:
            status, data = retry_request(
                lambda case=case: post_json(args.url, case["body"], args.timeout),
                args.attempts,
                args.retry_delay,
            )
            print_case_summary(case, status, data)
            assert_recommendation_payload(case, status, data)
        except Exception as exc:
            failures.append((case["name"], exc))
            print(f"FAILED: {case['name']}: {exc}", file=sys.stderr)

    if failures:
        print("\nFailures:", file=sys.stderr)
        for name, exc in failures:
            print(f"- {name}: {exc}", file=sys.stderr)
        return 1

    print("\nAll course recommendation API smoke cases passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Run Microsoft's PQTest engine; require success and a failing numeric control."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from generate import generate


def execute(executable, query, output):
    command = [str(executable), "run-test", "--queryFile", str(query), "--prettyPrint"]
    result = subprocess.run(command, capture_output=True, timeout=180)
    stdout = result.stdout.decode("utf-8-sig", errors="replace")
    stderr = result.stderr.decode("utf-8-sig", errors="replace")
    (output / (query.stem + ".stdout.json")).write_text(stdout, encoding="utf-8")
    (output / (query.stem + ".stderr.txt")).write_text(stderr, encoding="utf-8")
    try:
        parsed = json.loads(stdout)
    except ValueError as exc:
        raise AssertionError("PQTest did not return a JSON result; inspect retained output") from exc
    if isinstance(parsed, dict):
        parsed = [parsed]
    if not isinstance(parsed, list) or len(parsed) != 1 or not isinstance(parsed[0], dict):
        raise AssertionError("Expected one PQTest expression result")
    return result.returncode, parsed[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    manifest = generate(output)
    version = subprocess.run([str(args.executable), "version"], capture_output=True, check=True, timeout=30)
    (output / "pqtest-version.json").write_bytes(version.stdout)
    positive_code, positive = execute(args.executable, output / "acceptance.query.pq", output)
    negative_code, negative = execute(args.executable, output / "negative-control.query.pq", output)
    if positive_code != 0 or positive.get("Status") != "Passed":
        raise AssertionError("Native Power Query acceptance failed; inspect acceptance.query.stdout.json")
    if negative.get("Status") != "Failed":
        raise AssertionError("Deliberately incorrect numeric assertion was not rejected")
    # Check evaluated output only, never Details (which may contain the input source).
    if "OFFICE_NATIVE_ACCEPTANCE_PASS" not in json.dumps(positive.get("Output")):
        raise AssertionError("The expected evaluated output marker is missing")
    if "negative_control_zero" not in json.dumps(negative.get("Output")):
        raise AssertionError("Negative control failed for an unexpected reason")
    receipt = {**manifest, "schema": "financial-evidence.power-query-native-acceptance.v1",
               "status": "PASS", "engine": "Microsoft.PowerQuery.SdkTools 2.155.2 / PQTest.exe",
               "negative_control_rejected": True,
               "negative_control_process_code": negative_code,
               "pqtest_executable_sha256": hashlib.sha256(args.executable.read_bytes()).hexdigest(),
               "scope": "Microsoft Power Query runtime with synthetic Web.Contents fixtures; not Excel UI, live HTTP or customer adoption"}
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()

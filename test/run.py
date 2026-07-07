#!/usr/bin/env python3
"""Acceptance suite for the OKF statics port."""

import csv
import os
import subprocess
import sys


HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
RECEIPTS = os.path.join(HERE, "receipts", "old")
TMP = os.path.join(HERE, "tmp", "parity")
OKF = os.path.join(ROOT, "okf.py")
VIZ = os.path.join(ROOT, "viz.py")


def read_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def fixture_name(fixture):
    return fixture.replace("/", "__")


def run_cmd(argv):
    return subprocess.run([sys.executable, *argv], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def main():
    os.makedirs(TMP, exist_ok=True)
    with open(os.path.join(RECEIPTS, "LEDGER.tsv"), newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))

    failures = 0
    checks = 0

    for row in rows:
        fixture = row["fixture"]
        command = row["command"]
        expected_exit = int(row["exit"])
        stem = fixture_name(fixture)
        bundle = os.path.join(HERE, "fixtures", fixture)

        if command == "viz":
            stdout_path = os.path.join(TMP, f"{stem}__viz.out")
            html_path = os.path.join(TMP, f"{stem}__viz.html")
            result = run_cmd([VIZ, bundle, "--out", html_path])
            with open(stdout_path, "wb") as fh:
                fh.write(result.stdout)
            expected_stdout = read_bytes(os.path.join(RECEIPTS, row["stdout"]))
            expected_html = read_bytes(os.path.join(RECEIPTS, row["artifact"]))
            cases = [
                (f"{fixture} viz exit", result.returncode == expected_exit),
                (f"{fixture} viz stdout bytes", result.stdout == expected_stdout),
                (f"{fixture} viz html bytes", read_bytes(html_path) == expected_html),
            ]
        else:
            result = run_cmd([OKF, command, bundle])
            stdout_path = os.path.join(TMP, f"{stem}__{command}.out")
            with open(stdout_path, "wb") as fh:
                fh.write(result.stdout)
            expected_stdout = read_bytes(os.path.join(RECEIPTS, row["stdout"]))
            cases = [
                (f"{fixture} {command} exit", result.returncode == expected_exit),
                (f"{fixture} {command} stdout bytes", result.stdout == expected_stdout),
            ]

        for label, ok in cases:
            checks += 1
            if not ok:
                failures += 1
            print(f'{"ok  " if ok else "FAIL"}  {label}')

    if failures:
        print(f"\nFAIL: {failures}/{checks} check(s) failed")
        return 1
    print(f"\nALL PASS: {checks} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())

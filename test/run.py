#!/usr/bin/env python3
"""Acceptance suite for the OKF statics: byte-compares every tool output
against the ledgered receipts. `--accept` rewrites the receipts from the
current output (use after an intentional output change, then review the
diff in git)."""

import csv
import os
import shutil
import subprocess
import sys


HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
RECEIPTS = os.path.join(HERE, "receipts", "old")
TMP = os.path.join(HERE, "tmp", "parity")
OKF = os.path.join(ROOT, "okf.py")
VIZ = os.path.join(ROOT, "viz.py")


def read_bytes(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as fh:
        return fh.read()


def fixture_name(fixture):
    return fixture.replace("/", "__")


def run_cmd(argv):
    return subprocess.run([sys.executable, *argv], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def main(argv):
    accept = "--accept" in argv
    os.makedirs(TMP, exist_ok=True)
    with open(os.path.join(RECEIPTS, "LEDGER.tsv"), newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))

    failures = 0
    checks = 0
    accepted = 0

    for row in rows:
        fixture = row["fixture"]
        command = row["command"]
        expected_exit = int(row["exit"])
        stem = fixture_name(fixture)
        bundle = os.path.join(HERE, "fixtures", fixture)
        produced = []  # (produced path, receipt name)

        extra = (row.get("args") or "").split()
        suffix = command + ("__" + "_".join(a.lstrip("-") for a in extra) if extra else "")

        if command == "viz":
            stdout_path = os.path.join(TMP, f"{stem}__{suffix}.out")
            html_path = os.path.join(TMP, f"{stem}__{suffix}.html")
            result = run_cmd([VIZ, bundle, "--out", html_path, *extra])
            with open(stdout_path, "wb") as fh:
                fh.write(result.stdout)
            produced = [(stdout_path, row["stdout"]), (html_path, row["artifact"])]
        else:
            result = run_cmd([OKF, command, bundle, *extra])
            stdout_path = os.path.join(TMP, f"{stem}__{suffix}.out")
            with open(stdout_path, "wb") as fh:
                fh.write(result.stdout)
            produced = [(stdout_path, row["stdout"])]

        if accept:
            for src, receipt in produced:
                if read_bytes(os.path.join(RECEIPTS, receipt)) != read_bytes(src):
                    shutil.copyfile(src, os.path.join(RECEIPTS, receipt))
                    accepted += 1

        cases = [(f"{fixture} {command} exit", result.returncode == expected_exit)]
        for src, receipt in produced:
            label = "html bytes" if src.endswith(".html") else "stdout bytes"
            cases.append((f"{fixture} {command} {label}", read_bytes(src) == read_bytes(os.path.join(RECEIPTS, receipt))))

        for label, ok in cases:
            checks += 1
            if not ok:
                failures += 1
            print(f'{"ok  " if ok else "FAIL"}  {label}')

    if accept:
        print(f"\naccepted {accepted} receipt(s) — review with git diff")
    if failures:
        print(f"\nFAIL: {failures}/{checks} check(s) failed")
        return 1
    print(f"\nALL PASS: {checks} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

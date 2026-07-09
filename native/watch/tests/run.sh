#!/usr/bin/env bash
# Corre los tests de PlanCompute con swiftc (Foundation-only, sin Xcode).
set -euo pipefail
cd "$(dirname "$0")/.."
out="$(mktemp -d)/otf-plancompute-tests"
swiftc PlanModels.swift WatchStrings.swift PlanCompute.swift tests/PlanComputeTests.swift -o "$out"
"$out"

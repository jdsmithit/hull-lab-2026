#!/usr/bin/env bash
# Build the lab image locally and save offline tarballs for the USB stick (no registry needed).
# Usage: FACILITATOR_PIN=xxxx ./scripts/build.sh
# Each tarball loads as "hull-disclosure-labs", so the docker run command is the same everywhere.
set -euo pipefail
PIN="${FACILITATOR_PIN:-hull2026}"
cd "$(dirname "$0")/.."
mkdir -p dist
for arch in amd64 arm64; do
  docker buildx build --platform "linux/$arch" --build-arg FACILITATOR_PIN="$PIN" \
    -t hull-disclosure-labs --load .
  docker save -o "dist/hull-disclosure-labs-$arch.tar" hull-disclosure-labs
done
ls -lh dist/

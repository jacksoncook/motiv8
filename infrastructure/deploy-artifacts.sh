#!/usr/bin/env bash
set -euo pipefail

# deploy-artifacts.sh
#
# Builds + uploads:
#  - Frontend tarball to: s3://<UploadsBucket>/deployment/motiv8-fe-dist.tar.gz
#  - Backend tarball to:  s3://<UploadsBucket>/deployment/motiv8-be.tar.gz
#
# Usage:
#   ./deploy-artifacts.sh --bucket <UploadsBucket> --region us-east-1 \
#       --fe-dir /path/to/motiv8-fe --be-dir /path/to/motiv8-be
#
# Options:
#   --fe-only   Deploy only frontend
#   --be-only   Deploy only backend
#   --no-build  Skip builds; just package+upload based on existing build output / current repo state
#
# Notes:
#   - Frontend expects build output in dist/ (Vite) or build/ (CRA).
#   - Backend tarball uploads the entire backend directory (excluding common junk).
#     If you prefer building a wheel/docker image instead, tell me your desired packaging.

BUCKET=""
REGION="us-east-1"
FE_DIR=""
BE_DIR=""
FE_ONLY="false"
BE_ONLY="false"
NO_BUILD="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bucket) BUCKET="$2"; shift 2;;
    --region) REGION="$2"; shift 2;;
    --fe-dir) FE_DIR="$2"; shift 2;;
    --be-dir) BE_DIR="$2"; shift 2;;
    --fe-only) FE_ONLY="true"; shift 1;;
    --be-only) BE_ONLY="true"; shift 1;;
    --no-build) NO_BUILD="true"; shift 1;;
    -h|--help)
      sed -n '1,80p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown arg: $1"
      exit 1
      ;;
  esac
done

if [[ -z "$BUCKET" ]]; then
  echo "ERROR: --bucket is required"
  exit 1
fi

if [[ "$FE_ONLY" == "true" && "$BE_ONLY" == "true" ]]; then
  echo "ERROR: choose only one of --fe-only or --be-only (or neither for both)"
  exit 1
fi

if [[ "$BE_ONLY" != "true" && -z "$FE_DIR" ]]; then
  echo "ERROR: --fe-dir is required unless --be-only is set"
  exit 1
fi

if [[ "$FE_ONLY" != "true" && -z "$BE_DIR" ]]; then
  echo "ERROR: --be-dir is required unless --fe-only is set"
  exit 1
fi

S3_FE_KEY="deployment/motiv8-fe-dist.tar.gz"
S3_BE_KEY="deployment/motiv8-be.tar.gz"

tmpdir="$(mktemp -d)"
cleanup() { rm -rf "$tmpdir"; }
trap cleanup EXIT

deploy_frontend() {
  echo "==> Deploying frontend from: $FE_DIR"
  pushd "$FE_DIR" >/dev/null

  if [[ "$NO_BUILD" != "true" ]]; then
    if [[ -f package-lock.json ]]; then
      npm ci
    else
      npm install
    fi
    npm run build
  fi

  local out_dir="dist"
  if [[ ! -d "$out_dir" ]]; then
    out_dir="build"
  fi
  if [[ ! -d "$out_dir" ]]; then
    echo "ERROR: Frontend build output not found (expected dist/ or build/)."
    exit 1
  fi

  local tgz="$tmpdir/motiv8-fe-dist.tar.gz"
  rm -f "$tgz"
  tar -C "$(dirname "$out_dir")" -czf "$tgz" "$(basename "$out_dir")"

  aws s3 cp "$tgz" "s3://${BUCKET}/${S3_FE_KEY}" --region "$REGION"

  echo "Uploaded FE -> s3://${BUCKET}/${S3_FE_KEY}"
  popd >/dev/null
}

deploy_backend() {
  echo "==> Deploying backend from: $BE_DIR"

  # Resolve absolute path so we can tar from the parent directory
  local abs_be_dir parent base
  abs_be_dir="$(cd "$BE_DIR" && pwd)"
  parent="$(dirname "$abs_be_dir")"
  base="$(basename "$abs_be_dir")"   # e.g. "motiv8-be"

  if [[ "$NO_BUILD" != "true" ]]; then
    # Optional: run tests/lint here if you want
    true
  fi

  local tgz="$tmpdir/motiv8-be.tar.gz"
  rm -f "$tgz"

  # Create tarball that contains: <base>/...
  # So EC2 extraction to /app yields: /app/<base>/...
  tar -C "$parent" -czf "$tgz" \
    --exclude="$base/venv" \
    --exclude="$base/.venv" \
    --exclude="$base/__pycache__" \
    --exclude="$base/.pytest_cache" \
    --exclude="$base/.mypy_cache" \
    --exclude="$base/.git" \
    --exclude="$base/node_modules" \
    --exclude="$base/dist" \
    --exclude="$base/build" \
    --exclude="$base/*.log" \
    "$base"

  aws s3 cp "$tgz" "s3://${BUCKET}/${S3_BE_KEY}" --region "$REGION"
  echo "Uploaded BE -> s3://${BUCKET}/${S3_BE_KEY}"
}

if [[ "$BE_ONLY" != "true" ]]; then
  deploy_frontend
fi

if [[ "$FE_ONLY" != "true" ]]; then
  deploy_backend
fi

echo "Done."
echo "FE artifact: s3://${BUCKET}/${S3_FE_KEY}"
echo "BE artifact: s3://${BUCKET}/${S3_BE_KEY}"


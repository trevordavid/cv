#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p build
# The tracked PDF must never count as a successful build.
rm -f build/cv.pdf
for pass in 1 2 3; do
  xelatex -interaction=nonstopmode -halt-on-error -file-line-error \
    -no-shell-escape -output-directory=build cv.tex
done
test -s build/cv.pdf
pdfinfo build/cv.pdf > /dev/null
cp build/cv.pdf cv.pdf

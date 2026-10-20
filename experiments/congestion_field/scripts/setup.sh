#!/bin/sh
# Re-create the pristine baselines at pinned commits, build them, and build the field variants.
# Usage: sh experiments/congestion_field/scripts/setup.sh   (from the repository root)
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
mkdir -p third_party
clone() {  # url dir commit
  [ -d third_party/$2 ] || git clone -q --recursive "$1" third_party/$2
  git -C third_party/$2 checkout -q "$3"
  git -C third_party/$2 submodule update -q --init --recursive
}
clone https://github.com/Kei18/lacam3 lacam3 1c3ecf8ade40298f16047544634e9c0c1cf3b93c
clone https://github.com/Kei18/pibt2 pibt2 faab5b916649549f1cd563df8dbf6e4f6382f631
clone https://github.com/Jiaoyang-Li/EECBS EECBS 06ec70585dc4ad73177580a4ef91138335fd4d24

# baselines (unmodified sources).  pibt2 needs <cstring> on modern g++; it is force-included by a
# compiler flag so the baseline source stays untouched.  The same flag is used for the variant.
(cd third_party/lacam3 && cmake -B build -DCMAKE_BUILD_TYPE=Release >/dev/null && make -C build -j4 main)
(cd third_party/pibt2 && cmake -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS="-include cstring" >/dev/null && make -C build -j4 mapf)
(cd third_party/EECBS && cmake -B build -DCMAKE_BUILD_TYPE=RELEASE . >/dev/null && make -C build -j4)

# variants: copy the (unmodified) submodules next to the modified sources
mkdir -p variants/lacam3_field/third_party variants/pibt2_field/third_party
cp -a third_party/lacam3/third_party/argparse variants/lacam3_field/third_party/ 2>/dev/null || true
cp -a third_party/lacam3/third_party/googletest variants/lacam3_field/third_party/ 2>/dev/null || true
cp -a third_party/pibt2/third_party/grid-pathfinding variants/pibt2_field/third_party/ 2>/dev/null || true
cp -a third_party/pibt2/third_party/googletest variants/pibt2_field/third_party/ 2>/dev/null || true
(cd variants/lacam3_field && cmake -B build -DCMAKE_BUILD_TYPE=Release >/dev/null && make -C build -j4 main)
(cd variants/pibt2_field && cmake -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS="-include cstring" >/dev/null && make -C build -j4 mapf)
(cd variants/eecbs_field && cmake -B build -DCMAKE_BUILD_TYPE=RELEASE . >/dev/null && make -C build -j4)
echo "setup done"

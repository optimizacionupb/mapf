# Sources of reused code

All baseline code is used unmodified from these pinned commits (cloned into `third_party/` by
`scripts/setup.sh`, which is git-ignored). The baseline binaries are built from those pristine clones.

| baseline | repository | commit | licence |
|---|---|---|---|
| LaCAM3 | https://github.com/Kei18/lacam3 | 1c3ecf8ade40298f16047544634e9c0c1cf3b93c | MIT |
| PIBT (pibt2) | https://github.com/Kei18/pibt2 | faab5b916649549f1cd563df8dbf6e4f6382f631 | MIT |
| EECBS | https://github.com/Jiaoyang-Li/EECBS | 06ec70585dc4ad73177580a4ef91138335fd4d24 | USC Research License |

Build commands are the ones in each README, with these exceptions:
- `-DCMAKE_BUILD_TYPE=Release` is passed to all three.
- pibt2 needs `-DCMAKE_CXX_FLAGS="-include cstring"`, because its submodule `grid-pathfinding/graph/src/graph.cpp` uses `std::memset` without including `<cstring>`, which fails on g++ 13. The flag is used identically for the baseline and the variant, and no source file is edited.

## Variants (`variants/`)

Each variant is a full copy of its baseline. Only the files listed below differ, and each changed file starts with a `// MODIFIED for the congestion-field experiment. Original: <repo> @ <commit>, <path>` header.

- `variants/common/congestion_field.hpp` is new: the shared static and forecast field code.
- `variants/lacam3_field/` (from lacam3):
  - `main.cpp`: CLI flags and `field_time_ms` output.
  - `lacam3/CMakeLists.txt`: include path.
  - `lacam3/include/pibt.hpp`, `lacam3/src/pibt.cpp`: tie-breaker in the candidate sort.
  - `lacam3/include/planner.hpp`, `lacam3/src/planner.cpp`: field setup, plus a forecast once per high-level node.
- `variants/pibt2_field/` (from pibt2):
  - `mapf.cpp`: `field_time_ms` output.
  - `pibt2/CMakeLists.txt`: include path.
  - `pibt2/include/pibt.hpp`, `pibt2/src/pibt.cpp`: CLI flags, a forecast per timestep, and the tie-breaker. The unused macOS visualizer and openFrameworks submodule were removed from the copy.
- `variants/eecbs_field/` (from EECBS):
  - `CMakeLists.txt`: include path.
  - `inc/FieldGlue.h` is new.
  - `inc/Instance.h`: start and goal getters.
  - `inc/SingleAgentSolver.h`: `field_cost` and the FOCAL key.
  - `src/SpaceTimeAStar.cpp`: field accumulation.
  - `src/driver.cpp`: CLI flags and setup.

The benchmark maps and scenarios are the MovingAI files already in this repository, under `data/benchmarks/`.

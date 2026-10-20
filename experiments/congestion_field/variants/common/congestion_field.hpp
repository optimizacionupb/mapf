/*
 * Congestion field shared by the lacam3, pibt2 and EECBS variants.
 * Written for this experiment (not taken from any baseline repository).
 *
 * Two kinds of field are provided:
 *
 *   static   : H(v), the average per-timestep occupancy of v in baseline solutions of the tuning
 *              instances of the same map and agent count (built offline by scripts/build_heat.py).
 *
 *   forecast : F(v, t+k), k = 1..horizon, a time-indexed estimate of how many other agents will be at
 *              v at time t+k.  For k <= window it is the exact occupancy of committed paths (supplied
 *              by the host solver through a callback).  For k > window it is a prediction: every
 *              other agent is rolled forward along a deterministic shortest path towards its goal
 *              (ties broken by smaller vertex id) and deposits mass (1 - smooth) at its predicted
 *              vertex and smooth / deg spread over that vertex's neighbours.
 *
 * Both fields are consumed by score(): an agent standing at candidate vertex u is rolled forward on
 * its own greedy shortest path r_1 = u, r_2, ..., r_H and the score is
 *
 *     sum_{k=1..H} gamma^(k-1) * min(cap, field(r_k, k))
 *
 * The cap guarantees no vertex can look worse than `cap` agents, so a corridor is never effectively
 * closed.  The hosts only ever use the score as a TIE-BREAKER among candidates that the baseline
 * already considers equally good (same distance-to-goal in PIBT, same conflict count / within the
 * focal bound in EECBS), so the score never changes the set of moves or the cost bound the baseline
 * would accept.  See the guarantee comments at each integration point.
 */
#pragma once
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <fstream>
#include <functional>
#include <sstream>
#include <string>
#include <vector>

namespace cfield {

enum Mode { NONE = 0, STATIC = 1, FORECAST = 2 };

struct Params {
  Mode mode = NONE;
  float gamma = 0.8f;   // discount per future step
  int horizon = 10;     // H
  float cap = 2.0f;     // clip of the per-step field value
  float smooth = 0.5f;  // spatial smoothing share
  int window = 1;       // steps for which committed paths are used exactly
  bool beyond = true;   // ablation A: false -> no prediction beyond the window
  std::string heat_file;

  static Mode parse_mode(const std::string &s)
  {
    if (s == "static") return STATIC;
    if (s == "forecast") return FORECAST;
    return NONE;
  }
};

// wall-clock accounting of all field work (summed over threads), in nanoseconds
inline std::atomic<long long> &field_ns()
{
  static std::atomic<long long> ns{0};
  return ns;
}

struct ScopedTimer {
  std::chrono::steady_clock::time_point t0;
  ScopedTimer() : t0(std::chrono::steady_clock::now()) {}
  ~ScopedTimer()
  {
    field_ns() += std::chrono::duration_cast<std::chrono::nanoseconds>(
                      std::chrono::steady_clock::now() - t0)
                      .count();
  }
};

// distance oracle: dist(agent, vertex_id)
using DistFn = std::function<int(int, int)>;

struct Field {
  Params P;
  int V = 0;
  int N = 0;
  const std::vector<std::vector<int>> *adj = nullptr;  // vertex id -> neighbour ids
  std::vector<float> heat;                             // static mode
  std::vector<float> F;                                // forecast, index (k-1)*V + v
  std::vector<int> touched;
  std::vector<int> routes;  // agent j predicted vertex at k (0..H), index j*(H+1)+k

  void init(const Params &_P, int _V, int _N, const std::vector<std::vector<int>> *_adj)
  {
    P = _P;
    V = _V;
    N = _N;
    adj = _adj;
    if (P.mode == FORECAST) {
      F.assign((size_t)V * P.horizon, 0.f);
      routes.assign((size_t)N * (P.horizon + 1), -1);
    }
  }

  // heat file: one float per vertex id, whitespace separated (written by scripts/build_heat.py
  // using the host's vertex id order, see each host for how ids are mapped)
  bool load_heat_by_cell(const std::string &path, const std::vector<int> &vid_to_cell)
  {
    std::ifstream f(path);
    if (!f) return false;
    std::vector<float> cell;
    float x;
    while (f >> x) cell.push_back(x);
    heat.assign(V, 0.f);
    for (int v = 0; v < V; ++v) {
      int c = vid_to_cell[v];
      if (c < 0 || c >= (int)cell.size()) return false;
      heat[v] = cell[c];
    }
    return true;
  }

  template <class Dist>
  inline int greedy_next(int j, int v, const Dist &dist) const
  {
    int best = v, bd = dist(j, v);
    if (bd == 0) return v;
    for (int u : (*adj)[v]) {
      int du = dist(j, u);
      if (du < bd || (du == bd && u < best && best != v)) {
        best = u;
        bd = du;
      }
    }
    return best;
  }

  inline void deposit(int v, int k, float w)
  {
    float *row = &F[(size_t)(k - 1) * V];
    if (row[v] == 0.f) touched.push_back((k - 1) * V + v);
    row[v] += (1.f - P.smooth) * w;
    const auto &nb = (*adj)[v];
    if (!nb.empty() && P.smooth > 0.f) {
      float s = P.smooth * w / nb.size();
      for (int u : nb) {
        if (row[u] == 0.f) touched.push_back((k - 1) * V + u);
        row[u] += s;
      }
    }
  }

  // own contribution of agent j to F(v,k), so that an agent never avoids itself
  inline float own(int j, int v, int k) const
  {
    int g = routes[(size_t)j * (P.horizon + 1) + k];
    if (g < 0) return 0.f;
    if (g == v) return 1.f - P.smooth;
    const auto &nb = (*adj)[g];
    for (int u : nb)
      if (u == v) return P.smooth / nb.size();
    return 0.f;
  }

  // forecast from the current positions of all agents (positions[j] = vertex id)
  template <class Dist>
  void compute_forecast(const std::vector<int> &positions, const Dist &dist)
  {
    if (P.mode != FORECAST) return;
    ScopedTimer tm;
    for (int idx : touched) F[idx] = 0.f;
    touched.clear();
    const int H = P.horizon;
    for (int j = 0; j < N; ++j) {
      int v = positions[j];
      int *r = &routes[(size_t)j * (H + 1)];
      r[0] = v;
      for (int k = 1; k <= H; ++k) {
        v = greedy_next(j, v, dist);
        r[k] = v;
        if (P.beyond && k > P.window && P.gamma > 0.f) deposit(v, k, 1.f);
      }
    }
  }

  // committed(v, k): number of OTHER agents whose committed path is at v at time t+k (k <= window)
  template <class Dist, class Committed>
  float score(int i, int u, const Dist &dist, const Committed &committed) const
  {
    if (P.mode == NONE) return 0.f;
    // forecast with nothing beyond the window (ablations A and B): only k <= window matters
    const int kmax = (P.mode == FORECAST && (!P.beyond || P.gamma == 0.f))
                         ? std::min(P.window, P.horizon)
                         : P.horizon;
    float s = 0.f, w = 1.f;
    int v = u;
    for (int k = 1; k <= kmax; ++k) {
      if (k > 1) v = greedy_next(i, v, dist);
      float f;
      if (P.mode == STATIC) {
        f = heat[v];
      } else {
        f = 0.f;
        if (k <= P.window) {
          f += committed(v, k);
        } else if (P.beyond && P.gamma > 0.f) {
          f += std::max(0.f, F[(size_t)(k - 1) * V + v] - own(i, v, k));
        }
      }
      s += w * std::min(P.cap, f);
      w *= P.gamma;
      if (w == 0.f) break;
    }
    return s;
  }
};

}  // namespace cfield

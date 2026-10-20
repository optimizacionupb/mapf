// ADDED for the congestion-field experiment (not part of github.com/Jiaoyang-Li/EECBS @ 06ec705).
// Glue between EECBS's low-level focal search and the shared field in ../../common.
#pragma once
#include <queue>
#include "Instance.h"
#include "congestion_field.hpp"

struct EecbsField {
	cfield::Params P;
	int key_pos = 0;  // 0: off (baseline), 1: focal key after #conflicts, 2: after f
	int V = 0, N = 0;
	std::vector<std::vector<int>> adj;
	cfield::Field field;                     // scratch forecast grid F((k-1)*V + v)
	std::vector<float> committed;            // (k-1)*V + v, k <= window
	std::vector<int> committed_touched;
	std::vector<std::vector<int>> routes;    // predicted greedy shortest path of each agent from its start
	std::vector<float> weight;               // gamma^(k-1), k = 1..H

	void init(const Instance& ins, const cfield::Params& p, int _key_pos)
	{
		cfield::ScopedTimer tm;
		P = p;
		key_pos = _key_pos;
		V = ins.map_size;
		N = ins.getDefaultNumberOfAgents();
		adj.assign(V, {});
		for (int v = 0; v < V; v++)
			if (!ins.isObstacle(v))
				for (int u : ins.getNeighbors(v)) adj[v].push_back(u);
		// the shared Field is used only for its deposit/smoothing grid and heat loading
		cfield::Params q = P;
		if (q.mode == cfield::FORECAST) { q.mode = cfield::FORECAST; }
		field.init(q, V, N, &adj);
		if (P.mode == cfield::STATIC)
		{
			std::vector<int> id(V);
			for (int v = 0; v < V; v++) id[v] = v;  // EECBS loc == row * cols + col == cell index
			if (!field.load_heat_by_cell(P.heat_file, id)) { std::cerr << "cannot load heat\n"; exit(2); }
		}
		committed.assign((size_t)V * std::max(1, P.window), 0.f);
		weight.resize(P.horizon + 1);
		float w = 1.f;
		for (int k = 1; k <= P.horizon; k++) { weight[k] = w; w *= P.gamma; }
		// forecast for agents that have no path yet: greedy shortest path from the start
		routes.assign(N, {});
		if (P.mode == cfield::FORECAST)
		{
			for (int j = 0; j < N; j++)
			{
				std::vector<int> d(V, -1);
				std::queue<int> q2;
				d[ins.getGoal(j)] = 0;
				q2.push(ins.getGoal(j));
				while (!q2.empty())
				{
					int x = q2.front(); q2.pop();
					for (int u : adj[x]) if (d[u] < 0) { d[u] = d[x] + 1; q2.push(u); }
				}
				auto dist = [&](int, int v) { return d[v]; };
				int v = ins.getStart(j);
				routes[j].push_back(v);
				for (int k = 1; k <= P.horizon; k++) { v = field.greedy_next(j, v, dist); routes[j].push_back(v); }
			}
		}
	}

	// build the field seen by `agent` from the other agents' current paths (nullptr = not planned yet)
	void build(int agent, const std::vector<Path*>& paths)
	{
		if (P.mode != cfield::FORECAST) return;
		cfield::ScopedTimer tm;
		for (int idx : field.touched) field.F[idx] = 0.f;
		field.touched.clear();
		for (int idx : committed_touched) committed[idx] = 0.f;
		committed_touched.clear();
		const bool beyond = P.beyond && P.gamma > 0.f;
		for (int j = 0; j < N; j++)
		{
			if (j == agent) continue;
			const Path* p = paths[j];
			if (p != nullptr && !p->empty())
			{
				const int L = (int)p->size();
				for (int k = 1; k <= P.horizon; k++)
				{
					int v = (*p)[std::min(k, L - 1)].location;
					if (k <= P.window)
					{
						size_t idx = (size_t)(k - 1) * V + v;
						if (committed[idx] == 0.f) committed_touched.push_back(idx);
						committed[idx] += 1.f;
					}
					else if (beyond)
						field.deposit(v, k, 1.f);
				}
			}
			else if (beyond)
			{
				for (int k = 1; k <= P.horizon; k++) field.deposit(routes[j][k], k, 1.f);
			}
		}
	}

	// cost of being at v at time k (added to the node's accumulated field cost)
	inline float step(int v, int k) const
	{
		if (k < 1 || k > P.horizon) return 0.f;
		float f;
		if (P.mode == cfield::STATIC) f = field.heat[v];
		else if (k <= P.window) f = committed[(size_t)(k - 1) * V + v];
		else f = field.F[(size_t)(k - 1) * V + v];
		return weight[k] * std::min(P.cap, f);
	}
};

extern EecbsField* g_field;

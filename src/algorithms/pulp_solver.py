# src/algorithms/pulp_solver.py
from __future__ import annotations

import time
import uuid
import pulp

from domain.interfaces import MAPFSolver
from domain.models import AgentPath, ExecutionResult, Scenario, TrajectoryPoint

class PulpSolver(MAPFSolver):
    """Solver basado en Programación Entera Mixta (MILP) utilizando PuLP."""

    def __init__(self, timeout_s: float = 60.0) -> None:
        self.timeout_s = timeout_s

    @property
    def name(self) -> str:
        return "pulp_solver"

    def solve(self, scenario: Scenario, seed: int | None = None) -> ExecutionResult:
        start_time = time.perf_counter()
        topology = scenario.topology

        # 1. Extraer nodos y aristas dirigidas (incluyendo self-loops de espera)
        V = list(topology.nodes)
        E: list[tuple[int, int]] = []
        for u in V:
            E.append((u, u))  # Espera
            if u in topology.adjacency:
                for v, _ in topology.adjacency[u]:
                    E.append((u, v))

        # 2. Mapear agentes
        agents = scenario.agents
        R = list(range(len(agents)))
        robots = {i: {"start": agents[i].start, "goal": agents[i].goal} for i in R}

        # Validar si los nodos de inicio/meta existen
        if any(r["start"] not in V or r["goal"] not in V for r in robots.values()):
            return self._no_solution(scenario, seed, start_time)

        # Horizonte temporal
        T = max(15, len(V))
        K = range(1, T + 1)

        # 3. Crear modelo PuLP
        modelo = pulp.LpProblem("MAPF_MILP", pulp.LpMinimize)

        rho = {
            i: {
                e_idx: {
                    k: pulp.LpVariable(f"rho_{i}_{e_idx}_{k}", 0, 1, 'Integer')
                    for k in K
                }
                for e_idx in range(len(E))
            }
            for i in R
        }

        beta = pulp.LpVariable("Beta", 0, None, 'Integer')
        modelo += beta

        # Índices auxiliares para eficiencia
        salidas_de = {v: [] for v in V}
        entradas_a = {v: [] for v in V}
        entradas_reales_a = {v: [] for v in V}

        for e_idx, (a, b) in enumerate(E):
            salidas_de[a].append(e_idx)
            entradas_a[b].append(e_idx)
            if a != b:
                entradas_reales_a[b].append(e_idx)

        # 4. Restricciones del modelo MILP
        for i in R:
            origen = robots[i]["start"]
            modelo += (
                pulp.lpSum(rho[i][e_idx][1] for e_idx in salidas_de[origen]) == 1
            ), f"Inicio_robot_{i}"

        for i in R:
            for k in K:
                modelo += (
                    pulp.lpSum(rho[i][e_idx][k] for e_idx in range(len(E))) == 1
                ), f"UnaAristaPorInstante_{i}_{k}"

        for i in R:
            destino = robots[i]["goal"]
            modelo += (
                pulp.lpSum(
                    rho[i][e_idx][k]
                    for e_idx in entradas_reales_a[destino]
                    for k in K
                ) == 1
            ), f"Destino_robot_{i}"

        for j in V:
            for k in K:
                modelo += (
                    pulp.lpSum(rho[i][e_idx][k] for i in R for e_idx in entradas_a[j]) <= 1
                ), f"Capacidad_{j}_{k}"

        for i in R:
            for j in V:
                for k in range(1, T):
                    modelo += (
                        pulp.lpSum(rho[i][e_idx][k] for e_idx in entradas_a[j])
                        - pulp.lpSum(rho[i][e_idx][k + 1] for e_idx in salidas_de[j])
                        == 0
                    ), f"Flujo_{i}_{j}_{k}"

        for a, b in E:
            if a == b or (b, a) not in E:
                continue
            e_ab = E.index((a, b))
            e_ba = E.index((b, a))
            for k in K:
                modelo += (
                    pulp.lpSum(rho[i][e_ab][k] + rho[i][e_ba][k] for i in R) <= 1
                ), f"Swap_{a}_{b}_{k}"

        for i in R:
            destino = robots[i]["goal"]
            modelo += (
                pulp.lpSum(
                    k * rho[i][e_idx][k]
                    for e_idx in entradas_reales_a[destino]
                    for k in K
                ) <= beta
            ), f"Makespan_robot_{i}"

        # 5. Resolver
        solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=self.timeout_s)
        modelo.solve(solver)

        runtime_ms = (time.perf_counter() - start_time) * 1000.0
        status_str = pulp.LpStatus[modelo.status]

        if status_str == "Optimal":
            paths: list[AgentPath] = []
            sum_of_costs = 0.0
            makespan = 0

            for i in R:
                nodes = [robots[i]["start"]]
                for k in K:
                    for e_idx, (a, b) in enumerate(E):
                        val = pulp.value(rho[i][e_idx][k])
                        if val is not None and val > 0.5:
                            nodes.append(b)
                            break
                
                # Limpiar esperas redundantes al final si las hay
                while len(nodes) > 1 and nodes[-1] == nodes[-2] and nodes[-1] == robots[i]["goal"]:
                    nodes.pop()

                sum_of_costs += len(nodes) - 1
                makespan = max(makespan, len(nodes) - 1)

                paths.append(
                    AgentPath(
                        agent=agents[i].id,
                        trajectory=[TrajectoryPoint(node=n, time=t) for t, n in enumerate(nodes)],
                    )
                )

            return ExecutionResult(
                id=f"{scenario.id}_pulp_{uuid.uuid4().hex[:8]}",
                scenario_id=scenario.id,
                algorithm=self.name,
                status="success",
                paths=paths,
                seed=seed,
                runtime_ms=runtime_ms,
                makespan=int(pulp.value(beta)),
                sum_of_costs=sum_of_costs,
            )
        else:
            return self._no_solution(scenario, seed, start_time)

    def _no_solution(
        self, scenario: Scenario, seed: int | None, start_time: float
    ) -> ExecutionResult:
        return ExecutionResult(
            id=f"{scenario.id}_pulp_{uuid.uuid4().hex[:8]}",
            scenario_id=scenario.id,
            algorithm=self.name,
            status="no_solution",
            paths=[],
            seed=seed,
            runtime_ms=(time.perf_counter() - start_time) * 1000.0,
            makespan=0,
            sum_of_costs=0.0,
        )
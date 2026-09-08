# MAPF — Plano, agentes y nodos especiales

Prototipo del problema clásico de "Multi-Agent Path Finding" (MAPF): un plano modelado como un grafo, agentes que lo ocupan y se mueven entre nodos adyacentes, y nodos especiales que permiten compartir espacio de forma controlada mediante nodos sombra.

Documentación detallada de la arquitectura en [`docs/README.md`](docs/README.md).

## Modelo formal

El plano es un grafo no dirigido $G = (V, E)$. Sea $A$ el conjunto de agentes; cada agente ocupa exactamente un nodo:

$$\forall a \in A,\ \exists!\, v \in V : \text{pos}(a) = v$$

**Ocupación exclusiva** (fuera de los nodos prima $V' \subseteq V$):

$$\forall v \in V \setminus V',\ |\{a \in A : \text{pos}(a) = v\}| \leq 1$$

**Movimiento válido**: solo entre nodos adyacentes:

$$\text{mover}(a, u \to v) \text{ válido} \iff (u, v) \in E$$

**Nodos sombra**: cada $v' \in V'$ tiene un conjunto $S(v')$ de nodos sombra, cada uno conectado únicamente a $v'$. Si $a$ ocupa un $v'$ ya ocupado por $b$:

$$\text{pos}(b) = v' \land \text{mover}(a, u \to v') \implies \text{pos}(b) \leftarrow s,\ s \text{ nuevo} \in S(v')$$

Al regresar de $s$ a $v'$ libre, el nodo sombra se elimina: $S(v') \leftarrow S(v') \setminus \{s\}$.

## Cómo ejecutar

Requiere [`uv`](https://docs.astral.sh/uv/) y Python ≥ 3.12.

```bash
uv sync              # instala dependencias
uv run python -m mapf  # corre la demostración (carga el plano, mueve agentes, guarda capturas en temp/)
uv run pytest         # corre los tests
```

# Arquitectura

Documentación detallada del modelo. El [README](../README.md) de la raíz solo cubre el pitch, las restricciones formales y cómo correr el proyecto — esto es lo demás.

## Componentes

### `Plano`
Contenedor principal del grafo: carga nodos, los conecta, carga agentes, y ofrece `mover`, `estado_actual_to_dict` (serialización) y `visualizar_plano`.

### `Agente`
Entidad móvil con `id` y `posicion` (un `Nodo`). No puede ocupar un nodo ya ocupado, salvo mediante un nodo prima.

### `Nodo`
Vértice del grafo: `id`, `conexiones`, y el `agente` que lo ocupa (a lo sumo uno). Un movimiento solo es válido entre nodos adyacentes.

### `NodoPrima`
Hereda de `Nodo`. Permite que varios agentes compartan un mismo espacio físico, desplazando al ocupante actual a un nuevo `NodoSombra` cuando llega otro agente.

### `NodoSombra`
Nodo auxiliar de estacionamiento temporal, conectado únicamente a su `NodoPrima`. Al regresar de un nodo sombra a su nodo prima (ya libre), el nodo sombra se elimina.

## Esquema del JSON de entrada (`data/init.json`)

```json
{
  "nodos": [{"id": 1, "es_prima": true}],
  "conexiones": [[1, 2]],
  "agentes": [{"id": 1, "nodo_inicio": 1}]
}
```

- `nodos`: cada nodo con su `id` y si es o no `es_prima`.
- `conexiones`: pares de ids de nodos conectados.
- `agentes`: cada agente con su `id` y su `nodo_inicio`.

## Orden lógico de instanciación

1. Crear nodos.
2. Conectar nodos.
3. Crear agentes con su nodo de inicio.

## Trabajo futuro (fase 2: tiempo)

El siguiente paso es introducir el tiempo como dimensión del estado, para que la posición de cada agente dependa del instante en que se observa.

Un problema de diseño ya identificado — movimientos simultáneos dependientes:

En un plano en un tiempo $k$, dos agentes $i_1, i_2$ pueden moverse de forma que $i_1$ termine en la posición de $i_2$ en $k$, mientras $i_2$ termina en una posición distinta a la de $i_1$ en $k$:

$$\rho^{i_1}_{a,b,k} \land \rho^{i_2}_{b,c,k}, \quad c \neq a \neq b$$

Este par de movimientos es válido, pero requiere resolver el orden de ejecución. Solución propuesta:

1. Agrupar movimientos que comparten alguna posición.
2. Dentro de cada grupo, ordenar los movimientos de forma que se liberen primero las posiciones de las que dependan otras llegadas.

La representación temporal se implementará como snapshots por instante (no como copias completas del `Plano` por cada paso), guardando solo el estado (nodos, conexiones, agentes, posiciones) en cada instante.

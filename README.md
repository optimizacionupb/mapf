# MAPF - Plano, agentes y nodos especiales

Este es un prototipo para implementar el sistema propuesto en las reuniones del grupo sobre el problema de "Multi-Agent Path Finding" (MAPF).

La estructura del proyecto se centra en un plano que tiene las siguientes características:

- el plano es un grafo no dirigido;
- cada agente ocupa un nodo del grafo;
- cada movimiento avanza una unidad de espacio (un paso);
- existen nodos especiales que permiten compartir espacio de manera controlada;
- el siguiente paso es introducir la variable temporal para que cada posición dependa del instante en que se observa.

## 1. Arquitectura general

El sistema se organiza en los siguientes elementos principales:

### 1.1 Plano
La clase `Plano` es el contenedor principal del sistema. Se encarga de:

- cargar nodos;
- conectar nodos entre sí;
- cargar agentes;
- mantener la estructura del grafo;
- ofrecer utilidades para serializar el estado actual y para visualizar el plano.

La idea basa del plano es que cada nodo puede ser conectado con otros nodos y, por lo tanto, cada agente puede moverse solo entre nodos adyacentes.

### 1.2 Agente
La clase `Agente` representa una entidad móvil dentro del plano.

Cada agente tiene:

- un identificador único (`id`);
- una posición actual (`posicion`), que es un nodo del grafo.

La lógica del agente está centrada en que no puede ocupar un nodo ya ocupado por otro agente, salvo en casos especiales definidos por nodos primos y sombras.

### 1.3 Nodo
La clase `Nodo` representa un vértice del grafo del plano.

Tiene:

- `id`;
- `conexiones`;
- `agente` que actualmente ocupa ese nodo.

La restricción base es simple: un nodo puede estar ocupado por a lo más un agente, y el movimiento de un agente solo es válido si el destino es adyacente y no está ocupado.

### 1.4 Nodo prima
La clase `NodoPrima` hereda de `Nodo` y representa un caso especial.

Su propósito es permitir que varios agentes compartan un mismo espacio físico de forma controlada. Para esto, el nodo prima puede crear nodos sombra (`NodoSombra`) que funcionan como sitios temporales de estacionamiento.

Esto encaja con la idea descrita en `notas.md` de que exiten nodos especiales en los que se pueden crear nodos sombra para representar celdas de parqueadero.

### 1.5 Nodo sombra
La clase `NodoSombra` es un nodo auxiliar asociado a un `NodoPrima`.

Su comportamiento es específico:

- solo está conectado a su nodo prima;
- sirve como espacio temporal para un agente que no puede ocupar el nodo prima mientras otro ya lo está usando;
- si el agente sale del nodo sombra y regresa a su nodo prima asociado, el nodo sombra debe desaparecer del conjunto del nodo prima para mantener la consistencia del plano.

## 2. El comportamiento esperado del sistema

Las notas del proyecto dejan muy claro el funcionamiento conceptual:

- un agente solo puede ocupar un nodo en un instante i;
- los agentes, tiempos y nodos deben ser únicos;
- la lógica del movimiento debe garantizar que la transición sea válida en el plano;
- los nodos sombra se usan cuando múltiples agentes comparten un mismo destino o una misma entrada/salida;
- el plano no es solo un grafo estático: más adelante debe incorporar el tiempo como una dimensión del estado.

Esto se refleja en la descripción de `notas.md`, que además marca el orden lógico de instanciación del plano:

1. crear nodos;
2. conectar nodos;
3. crear agentes con su nodo de inicio.

## 3. Importancia de la estructura del JSON de entrada

El archivo `data/init.json` ofrece una estructura base para inicializar el plano:

```json
{
  "nodos": [
    {"id": 1, "es_prima": true},
    {"id": 2, "es_prima": false}
  ],
  "conexiones": [[1, 2]],
  "agentes": [
    {"id": 1, "nodo_inicio": 1}
  ],
  "tiempo": [1, 2, 3, 4, 5]
}
```

El JSON incluye:

- `nodos`: cada nodo con su `id` y si es o no `es_prima`;
- `conexiones`: pares de nodos conectados;
- `agentes`: cada agente con su `id` y su `nodo_inicio`;
- `tiempo`: el conjunto temporal del plano (como diseño inicial del plano temporal).

## 4. Dependencias circulares: un problema no menor

Dentro de la arquitectura, existe una preocupación importante y explícita en el desarrollo:

- `agente.py` depende de `nodo.py`;
- `nodo.py` depende de `agente.py`;
- `nodo_prima.py` y `nodo_sombra.py` también se relacionan entre sí.

Esto provoca un patrón de dependencias circulares. En Python, esas dependencias pueden romper la importación del módulo si se resuelven de forma incorrecta en tiempo de ejecución.

La estrategia recomendada para resolver esto es:

- no depender de imports de runtime entre módulos que se referencian mutuamente;
- usar `TYPE_CHECKING` para anotaciones estáticas;
- importar dentro de funciones cuando realmente hace falta evaluar el tipo en runtime;
- reestructurar la lógica para que la coordinación del movimiento quede en capas más claras.

Esto es una necesidad arquitectónica importante, porque la idea del modelo es buena, pero si la dependencia circular no se controla, el sistema falla antes incluso de evaluar la lógica de movimiento o de tiempo.

## 5. Estado de implementación del plano temporal

El proyecto todavía no implementa el plano temporal de forma real.

La clase `PlanoTemporal` en `plano_temporal.py` solo incorpora una propiedad `tiempo` extra y procesa la lista de tiempos del JSON. Hasta aquí, no está modelado el comportamiento central que define un plano temporal:

- la posición de un agente depende del tiempo;
- la ocupación del nodo depende del instante;
- cada movimiento consumirá un paso temporal;
- la validación debe hacerse simultáneamente para todos los agentes del siguiente instante.

Es decir, la restricción temporal no está todavía implementada en la lógica del movimiento ni en la gestión del estado. En este punto, `PlanoTemporal` es solo una extensión inicial de la estructura, no una versión funcional del espacio temporal.

## 6. Cómo se piensa implementar la temporalidad

La idea planteada en el proyecto, y la más natural para este diseño, es implementar la temporalidad mediante snapshots por instante.

La idea es:

- el grafo base sigue siendo el mismo;
- cada instante temporal tiene su propio estado del plano;
- el estado del plano en tiempo `t` se representa por las posiciones actuales de los agentes, la ocupación de cada nodo y los eventos relevantes (por ejemplo, nodos sombra asociados a nodos prima);
- en el paso `t -> t+1`, todos los agentes proponen su movimiento o permanencia;
- el sistema valida el conjunto completo de movimientos para ese paso antes de confirmarlo.

Esto permite que el sistema no tenga que mantener en memoria `n` objetos `Plano` completos para cada paso temporal; en su lugar, se puede guardar solo un snapshot del estado en cada instante, por ejemplo en formato JSON.

La estrategia sugerida es:

- guardar el estado del plano en snapshots serializables;
- usar una estructura tipo:

```python
snapshots = {
  0: {...estado inicial...},
  1: {...estado tras paso 1...},
  2: {...estado tras paso 2...}
}
```

donde cada estado contiene:

- nodos,
- conexiones,
- agentes,
- posiciones actuales,
- ocupación por instante.

Esto evita cargar en memoria una copia entera del grafo para cada paso temporal y hace más sencillo reconstruir un estado concreto del sistema desde un JSON.

En otras palabras, la temporalidad se implementaría como una secuencia de estados del plano, no como una duplicación completa de objetos `Plano` por cada tiempo.

## 7. Serialización del estado actual

La clase `Plano` incluye el método `estado_actual_to_dict()`, que serializa el estado actual del plano a un diccionario compatible con un JSON de inicialización.

Esto es útil porque permite:

- guardar snapshots de un estado concreto;
- restaurar el plano más tarde;
- depurar y comparar estados entre pasos;
- apoyar la idea de snapshots temporales.

La serialización incluye:

- nodos con `id` y `es_prima`;
- conexiones;
- agentes con su posición actual;
- eventualmente, información temporal si el plano temporal ya se ha implementado.

## 8. Visualización del plano

El proyecto también incluye una visualización del plano mediante `matplotlib` y `networkx`.

La idea es dibujar:

- nodos normales en un color;
- nodos primos en otro color;
- nodos sombra como conexiones auxiliares del nodo prima;
- agentes sobre su nodo actual con etiquetas `A<id>`.

Esto ayuda mucho a conceptualizar el mapa, especialmente durante la validación de movimientos o durante la depuración del comportamiento del plano.

## 9. Flujo del main.py

El archivo `main.py` actúa como ejemplo de uso del proyecto y como mini-demostración funcional.

El flujo del programa es el siguiente:

1. Se carga el JSON de entrada.
   - se toma el contenido de `data/init.json`;
   - se convierte a un diccionario Python;
   - ese diccionario se usa para construir un `Plano`.

2. Se inicializa el plano.
   - se crean todos los nodos;
   - se conectan;
   - se crean todos los agentes y se ubican según su `nodo_inicio`.

3. Se imprime el estado inicial.
   - se muestran los agentes y la posición de cada uno.

4. Se intenta ejecutar movimientos legales.
   - se usa `plano.mover(nodo_id, agente_id)`;
   - si el movimiento es válido, se confirma;
   - si falla, se captura con `try/except` y se imprime la excepción.

5. Se guarda un snapshot JSON del estado actual.
   - se usa `estado_actual_to_dict()`;
   - se escribe en la carpeta `temp`.

6. Se renderiza la visualización del estado actual.
   - se guarda una imagen PNG en `temp`;
   - esto facilita inspeccionar el grafo y la posición de los agentes.

7. Se intenta ejecutar movimientos ilegales.
   - un destino no adyacente, un nodo ocupado o una regla especial del nodo prima produce una excepción;
   - la ejecución se captura y se imprime para ver qué validación está fallando.

8. Se guarda un nuevo snapshot del estado final.
   - se escribe otro JSON de estado;
   - se vuelve a guardar la visualización del plano final.

Este flujo es útil porque muestra dos cosas al mismo tiempo:

- la capacidad del sistema para evaluar movimientos válidos e inválidos;
- la posibilidad de serializar y visualizar los estados del plano para comprobar el comportamiento.

## 10. Conclusión

El proyecto tiene una base sólida y bien orientada:

- un grafo de nodos y conexiones;
- una lógica simple pero clara de movimiento;
- una extensión natural para `NodoPrima` y `NodoSombra`;
- una idea correcta de serializar estados y guardar snapshots;
- una visión clara de que la temporalidad debe introducirse como una capa de estados por instante.

Sin embargo, el punto más importante que falta es la parte temporal real:

- el sistema todavía no hace que la posición dependa del instante de tiempo de manera consistente;
- no hay validación simultánea de todos los movimientos del siguiente paso;
- no hay una política de transición completa del plano temporal.

Por eso el futuro diseño debe enfocarse en:

1. resolver las dependencias circulares;
2. dejar claro el manejo del estado por instante;
3. validar movimientos de forma simultánea;
4. serializar snapshots JSON por cada paso temporal;
5. guardar esos estados para reconstruir el historial sin materializar `n` planos completos en memoria.

Este enfoque hace que el sistema sea más mantenible, más fácil de depurar y más cercano a la forma en que un plano temporal realmente debería operar.

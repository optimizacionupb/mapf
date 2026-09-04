# Notas — Plano

## Descripción
Esta es la clase principal; representa un plano construido a partir de nodos. Debe almacenar y gestionar agentes, tiempo discreto y su interacción con los nodos.

## Restricciones
- Los agentes, tiempos y nodos deben ser únicos.
- Un agente solo puede ocupar un nodo en un tiempo i.

## Orden lógico de instanciación del plano
1. Crear nodos
2. Definir conexiones entre nodos
3. Crear agente con nodo de entrada

## Comportamientos especiales
Hay nodos especiales en los que se pueden crear nodos sombra que funcionan como celdas de parqueadero. Un nodo sombra está relacionado a un nodo prima y únicamente está conectado a su nodo prima.

### Uso de nodo sombra
El nodo sombra solo se crea cuando:
- Múltiples agentes tienen un mismo nodo de salida.
- Un agente DEBE pasar por el nodo final de otro agente cuando el segundo ya esté ocupando dicho nodo.
- Múltiples agentes tienen el mismo nodo como final.

## Definir
El comportamiento de nodos con soporte de nodos sombra se puede implementar de dos formas diferentes:
1. Crear nuevos nodos con identificación especial (ej. id negativo) en la clase Plano.
2. Crear una clase hija para la clase Nodo que autocontenga los nodos sombras.

## Implementación de movimiento de agentes
- Definir una API de movimiento con `agente.mover(destino)` como punto de entrada.
- La validación de movimiento debe garantizar que un agente solo pueda desplazarse a nodos adyacentes (conectados al nodo origen).
- La ejecución base puede implementarse en `Nodo`, con posibilidad de sobrescribirla en clases hijas para comportamientos especiales.
- En `NodoPrima`, si el agente se mueve desde un nodo sombra hacia el nodo prima asociado, el nodo sombra debe eliminarse para mantener la consistencia del plano.


# Notas originales (Sin formato)
DESCRIPCIÓN:
Esta es la clase principal, representa un plano construído a partir de nodos.
Debe de almacenar y gestionar agentes, tiempo discreto y su interacción con los nodos.

RESTRICCIONES:
Los agentes, tiempos y nodos deben ser únicos.
Un agente solo puede ocupar un nodo en un tiempo i

ORDEN LÓGICO INSTANCIACIÓN PLANO:
1. Crear nodos
2. Definir conexiones entre nodos
3. Crear agente con nodo de entrada

COMPORTAMIENTOS ESPECIALES:
Hay nodos especiales en los que se pueden crear nodos sombra que funcionan como celdas de
parqueadero. Un nodo sombra está relacionado de a un nodo principal. El nodo sombra
únicamente está conectado a su nodo principal.
    USO NODO SOMBRA:
    El nodo sombra solo se crea cuando:
    - Múltiples agentes tienen un mismo nodo de salida
    - Un agente DEBE pasar por el nodo final de otro agente cuando el segundo ya esté
    ocupando dicho nodo
    - Múltiples agentes tienen el mismo nodo como final

DEFINIR:
El comportamiento de nodos con soporte de nodos sombra se puede implementar de dos formas diferentes:
1. Crear nuevos nodos con identificación especial (ej. id negativo) en la clase Plano
2. Crear una clase hija para la clase Nodo que autocontenga los nodos sombras

IMPLEMENTACIÓN DE MOVIMIENTO DE AGENTES:
Definir una API de movimiento con `agente.mover(destino)` como punto de entrada.
La validación de movimiento debe garantizar que un agente solo pueda desplazarse a nodos
adyacentes (conectados al nodo origen). La ejecución base puede implementarse en `Nodo`,
con posibilidad de sobrescribirla en clases hijas para comportamientos especiales.
En `NodoPrima`, si el agente se mueve desde un nodo sombra hacia el nodo prima asociado,
el nodo sombra debe eliminarse para mantener la consistencia del plano.
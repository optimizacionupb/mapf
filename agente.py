from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nodo import Nodo


class Agente:
    id: int
    posicion: Nodo

    def __init__(self, id: int, nodo: Nodo) -> None:
        self.id = id
        self.set_posicion(nodo)

    def mover(self, nodo: Nodo):
        self.posicion.mover_agente(nodo)

    def set_posicion(self, nodo: Nodo) -> None:
        if nodo.agente is None:
            nodo.agente = self
            self.posicion = nodo
            return

        from nodo_prima import NodoPrima

        if isinstance(nodo, NodoPrima):
            nodo.mover_a_sombra()
            nodo.agente = self
            self.posicion = nodo
            return

        raise Exception('Intento de asignar un agente a un nodo ocupado no prima.')

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Agente):
            return False
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

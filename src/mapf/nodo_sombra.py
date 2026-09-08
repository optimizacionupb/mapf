from __future__ import annotations

from typing import TYPE_CHECKING

from mapf.nodo import Nodo

if TYPE_CHECKING:
    from mapf.nodo_prima import NodoPrima


class NodoSombra(Nodo):
    """Nodo auxiliar de estacionamiento temporal, asociado a un nodo prima."""

    nodo_prima: NodoPrima

    def __init__(self, id: int, nodo_prima: NodoPrima) -> None:
        super().__init__(id)
        self.nodo_prima = nodo_prima

    def mover_agente(self, nodo: Nodo) -> None:
        """Mueve el agente de este nodo sombra de vuelta a su nodo prima."""
        if self.nodo_prima != nodo:
            raise Exception('Intento de mover un agente a un nodo incorrecto.')
        if self.nodo_prima.agente is not None:
            raise Exception('Intento de ocupar un nodo prima ya ocupado.')

        self.nodo_prima.agente = self.agente
        self.agente.posicion = self.nodo_prima
        self.agente = None
        self.nodo_prima.remove_sombra(self)

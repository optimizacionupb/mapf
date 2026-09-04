from __future__ import annotations

from typing import TYPE_CHECKING

from nodo import Nodo

import variables_globales as globals

if TYPE_CHECKING:
    from agente import Agente
    from nodo_sombra import NodoSombra


class NodoPrima(Nodo):
    """Nodo que permite ocuparlo con varios agentes mediante nodos sombra."""

    nodos_sombra: set["NodoSombra"]

    def __init__(self, id: int):
        self.nodos_sombra = set()
        super().__init__(id=id)

    def inicializar_agente(self, agente: Agente) -> None:
        if self.agente is not None:
            self.mover_a_sombra()
        self.agente = agente

    def mover_a_sombra(self):
        sombra = self.crear_nodo_sombra()
        self.mover_agente(nodo_destino=sombra)

    def crear_nodo_sombra(self):
        from nodo_sombra import NodoSombra

        sombra = NodoSombra(globals.contador, self)
        sombra.conectar(self)
        self.nodos_sombra.add(sombra)
        globals.contador -= 1
        return sombra

    def remove_sombra(self, sombra: "NodoSombra"):
        self.nodos_sombra.discard(sombra)

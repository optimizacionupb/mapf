from __future__ import annotations

from typing import TYPE_CHECKING

from mapf.nodo import Nodo

if TYPE_CHECKING:
    from mapf.agente import Agente
    from mapf.nodo_sombra import NodoSombra


class NodoPrima(Nodo):
    """Nodo que permite ocuparlo con varios agentes mediante nodos sombra."""

    _contador_sombra: int = -1

    nodos_sombra: set[NodoSombra]

    def __init__(self, id: int) -> None:
        self.nodos_sombra = set()
        super().__init__(id=id)

    @classmethod
    def reiniciar_contador(cls, valor_inicial: int) -> None:
        """Reinicia el contador de ids de nodos sombra."""
        cls._contador_sombra = valor_inicial

    def inicializar_agente(self, agente: Agente) -> None:
        """Asigna un agente al nodo prima, desplazando al ocupante actual a una sombra."""
        if self.agente is not None:
            self.mover_a_sombra()
        self.agente = agente

    def mover_a_sombra(self) -> None:
        """Desplaza al agente actual de este nodo hacia un nuevo nodo sombra."""
        sombra = self.crear_nodo_sombra()
        self.mover_agente(nodo_destino=sombra)

    def crear_nodo_sombra(self) -> NodoSombra:
        """Crea y conecta un nuevo nodo sombra asociado a este nodo prima."""
        from mapf.nodo_sombra import NodoSombra

        sombra = NodoSombra(NodoPrima._contador_sombra, self)
        sombra.conectar(self)
        self.nodos_sombra.add(sombra)
        NodoPrima._contador_sombra -= 1
        return sombra

    def remove_sombra(self, sombra: NodoSombra) -> None:
        """Elimina un nodo sombra de este nodo prima."""
        self.nodos_sombra.discard(sombra)

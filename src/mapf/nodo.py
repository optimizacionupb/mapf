from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mapf.agente import Agente


class Nodo:
    """Representa un nodo del plano, con un id único y sus conexiones."""

    id: int
    conexiones: set[Nodo]
    agente: Agente | None

    def __init__(self, id: int) -> None:
        self.id = id
        self.conexiones = set()
        self.agente = None

    def inicializar_agente(self, agente: Agente) -> None:
        """Asigna un agente a este nodo si está libre."""
        if self.agente is not None:
            raise Exception('Intento de ocupar un nodo ya ocupado.')
        self.agente = agente

    def mover_agente(self, nodo_destino: Nodo) -> None:
        """Mueve el agente de este nodo hacia nodo_destino."""
        from mapf.nodo_prima import NodoPrima

        if nodo_destino not in self.conexiones:
            raise Exception('Intento de mover un agente a un nodo no adyacente.')
        if nodo_destino.agente is not None and not isinstance(nodo_destino, NodoPrima):
            raise Exception('Intento de ocupar un nodo ya ocupado.')
        if isinstance(nodo_destino, NodoPrima) and nodo_destino.agente is not None:
            nodo_destino.mover_a_sombra()
        nodo_destino.agente = self.agente
        self.agente.posicion = nodo_destino
        self.agente = None

    def conectar(self, other: Nodo) -> None:
        """Conecta este nodo con otro nodo (bidireccional)."""
        self.conexiones.add(other)
        other.conexiones.add(self)

    def __str__(self) -> str:
        return f"Node {self.id}: {', '.join(str(n.id) for n in self.conexiones)}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Nodo):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

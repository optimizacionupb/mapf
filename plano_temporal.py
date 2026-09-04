from typing import Iterable, TYPE_CHECKING, TypedDict

from overrides import overrides

from plano import Plano

if TYPE_CHECKING:
    from nodo import Nodo

class MovimientosInfo(TypedDict):
    agente: int
    nodo: int

class PlanoTemporal(Plano):
    tiempo: tuple[int, ...]
    ubicaciones: set[tuple[Nodo, int]]
    tiempo_actual: int

    def __init__(self, init: dict):
        super().__init__(init)
        self.tiempo = self.procesar_tiempo(init["tiempo"])
        self.inicializar_tiempo()
        self.ubicaciones = set()
        self.tiempo_actual = self.tiempo[0]

    def mover_temporalmente(self, movimientos: list[MovimientosInfo]):
        for movimiento in movimientos:
            agente_id = movimiento["agente"]
            nodo_id = movimiento["nodo"]
            self.mover(agente_id=agente_id, nodo_id=nodo_id)

    def inicializar_tiempo(self):
        for nodo in self.nodos:
            self.ubicaciones.add(tuple(nodo, self.tiempo[0]))

    # Añadir a self.tiempo el contenido de la llave tiempo del dict init
    @staticmethod
    def procesar_tiempo(tiempo: Iterable[int]) -> tuple[int, ...]:
        tiempo_procesado = list(tiempo)
        tiempo_procesado.sort()
        tiempo_procesado = tuple(tiempo_procesado)
        return tiempo_procesado


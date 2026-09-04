

class Nodo:
    from agente import Agente
    """
    Representa un nodo dentro de un plano.

    Cada nodo tiene un identificador único y una colección de
    nodos adyacentes a los que está conectado.


    :param id: Identificador único del nodo en el grafo.
    :param conexiones: Conjunto de nodos conectados directamente a este nodo.
    :param agente: Agente que ocupa el nodo.
    """

    # Identificador único del nodo dentro del grafo.
    id: int

    # Conjunto de nodos adyacentes únicos conectados directamente con este nodo.
    conexiones: set["Nodo"]

    # Agente que ocupa el nodo.
    agente: Agente | None

    def __init__(self, id: int) -> None:
        self.id = id
        self.conexiones = set()
        self.agente = None

    def inicializar_agente(self, agente: Agente) -> None:
        # Funciona a modo de setter
        if self.agente is not None:
            # TODO: crear excepción personalizada para intento de ocupar un nodo ya ocupado
            raise Exception
        self.agente = agente

    def mover_agente(self, nodo_destino: "Nodo") -> None:
        from nodo_prima import NodoPrima
        """
        Mueve un agente de este nodo a otro nodo.

        :param agente: El agente a mover.
        :param nodo_destino: El nodo al que se moverá el agente.
        :return: None
        """
        if nodo_destino not in self.conexiones:
            # TODO: crear excepción personalizada para movimiento inválido
            raise Exception
        if nodo_destino.agente is not None and not isinstance(nodo_destino, NodoPrima):
            # TODO: crear excepción personalizada para intento de ocupar un nodo ya ocupado
            raise Exception
        if isinstance(nodo_destino, NodoPrima) and nodo_destino.agente is not None:
            nodo_destino.mover_a_sombra()
        nodo_destino.agente = self.agente
        self.agente.posicion = nodo_destino
        self.agente = None
    def conectar(self, other: "Nodo"):
        """
        Conecta este nodo con otro nodo.
        :param other: Nodo adyacente al nodo que se hace referencia
        """
        self.conexiones.add(other)
        other.conexiones.add(self)

    def __str__(self):
        return f"Node {self.id}: {', '.join(str(n.id) for n in self.conexiones)}"


    # Se necesitan definir __hash__() y __eq__() para poder ingresar objetos tipo Nodo a
    # Por defecto, un objeto dinámico no es hashable
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Nodo):
            return False
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)
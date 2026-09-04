from __future__ import annotations

from pathlib import Path
from typing import Iterable, TypedDict

from agente import Agente
from nodo import Nodo
from nodo_prima import NodoPrima


class NodoInfo(TypedDict):
    id: int
    es_prima: bool


class AgenteInfo(TypedDict):
    id: int
    nodo_inicio: int


class Plano:
    nodos: dict[int, Nodo]
    agentes: dict[int, Agente]

    def __init__(self, init: dict):
        self.nodos = {}
        self.agentes = {}
        self.cargar_nodos(init['nodos'])
        self.conectar_nodos(init['conexiones'])
        self.cargar_agentes(init['agentes'])

    def cargar_nodos(self, nodos_info: Iterable[NodoInfo]):
        for info in nodos_info:
            n_id = info['id']
            es_prima = info['es_prima']
            self.nodos[n_id] = NodoPrima(id=n_id) if es_prima else Nodo(id=n_id)

    def mover(self, nodo_id: int, agente_id: int):
        agente = self.agentes[agente_id]
        nodo = self.nodos[nodo_id]
        agente.posicion.mover_agente(nodo)

    def set_posicion_agente(self, agente_id: int, nodo: Nodo) -> None:
        agente = self.agentes[agente_id]
        if nodo.agente is None:
            nodo.agente = agente
            agente.posicion = nodo
            return

        if isinstance(nodo, NodoPrima):
            nodo.mover_a_sombra()
            nodo.agente = agente
            agente.posicion = nodo
            return

        raise Exception('Intento de asignar un agente a un nodo ocupado no prima.')

    def conectar_nodos(self, conexiones: Iterable[list[int] | tuple[int, int]]):
        for con in conexiones:
            n_1 = con[0]
            n_2 = con[1]
            if n_1 not in self.nodos or n_2 not in self.nodos:
                raise Exception('Se intenta conectar nodos inexistentes.')
            self.nodos[n_1].conectar(self.nodos[n_2])

    def cargar_agentes(self, agente_info: Iterable[AgenteInfo]):
        for info in agente_info:
            a_id = info['id']
            n_id = info['nodo_inicio']
            if n_id not in self.nodos:
                raise Exception(f'El nodo de inicio {n_id} no existe.')
            agente = Agente(id=a_id, nodo=self.nodos[n_id])
            self.agentes[a_id] = agente

    def estado_actual_to_dict(self):
        nodos = [
            {'id': nodo.id, 'es_prima': isinstance(nodo, NodoPrima)}
            for nodo in sorted(self.nodos.values(), key=lambda n: n.id)
        ]

        conexiones = []
        visitadas = set()
        for nodo in sorted(self.nodos.values(), key=lambda n: n.id):
            for vecino in sorted(nodo.conexiones, key=lambda n: n.id):
                par = tuple(sorted((nodo.id, vecino.id)))
                if par in visitadas:
                    continue
                visitadas.add(par)
                conexiones.append([par[0], par[1]])

        agentes = [
            {'id': agente.id, 'nodo_inicio': agente.posicion.id}
            for agente in sorted(self.agentes.values(), key=lambda a: a.id)
        ]

        estado = {
            'nodos': nodos,
            'conexiones': conexiones,
            'agentes': agentes,
        }

        if hasattr(self, 'tiempo'):
            estado['tiempo'] = list(self.tiempo)

        return estado

    def visualizar_plano(self, output_path: str | None = None):
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import networkx as nx

        if output_path is None:
            output_path = Path(__file__).resolve().parent / 'temp' / 'plano.png'
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        grafo = nx.Graph()
        for nodo in self.nodos.values():
            grafo.add_node(nodo)
            for vecino in nodo.conexiones:
                if nodo.id < vecino.id:
                    grafo.add_edge(nodo, vecino)
            if isinstance(nodo, NodoPrima):
                for sombra in nodo.nodos_sombra:
                    grafo.add_node(sombra)
                    grafo.add_edge(nodo, sombra)

        posiciones = nx.spring_layout(grafo, seed=42)

        nodos_normales = [n for n in self.nodos.values() if not isinstance(n, NodoPrima)]
        nodos_primas = [n for n in self.nodos.values() if isinstance(n, NodoPrima)]
        nodos_sombra = [sombra for nodo in self.nodos.values() if isinstance(nodo, NodoPrima) for sombra in nodo.nodos_sombra]

        fig, ax = plt.subplots(figsize=(8, 8))
        nx.draw_networkx_edges(grafo, posiciones, width=1.8, alpha=0.9, ax=ax)
        nx.draw_networkx_nodes(
            grafo,
            posiciones,
            nodelist=nodos_normales,
            node_color='lightblue',
            node_size=600,
            edgecolors='black',
            linewidths=1,
            ax=ax,
        )
        nx.draw_networkx_nodes(
            grafo,
            posiciones,
            nodelist=nodos_primas,
            node_color='tomato',
            node_size=700,
            edgecolors='black',
            linewidths=1,
            ax=ax,
        )
        if nodos_sombra:
            nx.draw_networkx_nodes(
                grafo,
                posiciones,
                nodelist=nodos_sombra,
                node_color='silver',
                node_size=300,
                edgecolors='black',
                linewidths=1,
                ax=ax,
            )

        labels = {
            nodo: str(nodo.id) if not hasattr(nodo, 'nodo_prima') else ''
            for nodo in grafo.nodes
        }
        nx.draw_networkx_labels(grafo, posiciones, labels=labels, font_size=10, font_color='black', ax=ax)

        for agente in self.agentes.values():
            if agente.posicion not in posiciones:
                continue
            x, y = posiciones[agente.posicion]
            ax.text(x, y + 0.08, f'A{agente.id}', ha='center', va='center', fontsize=9, fontweight='bold', color='black')

        ax.set_title('Plano')
        ax.axis('off')
        fig.tight_layout()
        fig.savefig(output_path, dpi=200)
        plt.close(fig)
        return output_path

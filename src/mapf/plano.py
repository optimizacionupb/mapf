from __future__ import annotations

from pathlib import Path
from typing import Iterable, TypedDict

from mapf.agente import Agente
from mapf.config import cargar_config
from mapf.nodo import Nodo
from mapf.nodo_prima import NodoPrima


class NodoInfo(TypedDict):
    id: int
    es_prima: bool


class AgenteInfo(TypedDict):
    id: int
    nodo_inicio: int


class Plano:
    """Grafo no dirigido de nodos, con los agentes que los ocupan."""

    nodos: dict[int, Nodo]
    agentes: dict[int, Agente]
    config: dict

    def __init__(self, init: dict, config: dict | None = None) -> None:
        self.config = config if config is not None else cargar_config()
        self.nodos = {}
        self.agentes = {}
        NodoPrima.reiniciar_contador(self.config['ids']['sombra_id_inicio'])
        self.cargar_nodos(init['nodos'])
        self.conectar_nodos(init['conexiones'])
        self.cargar_agentes(init['agentes'])

    def cargar_nodos(self, nodos_info: Iterable[NodoInfo]) -> None:
        """Crea todos los nodos del plano (prima o normales)."""
        for info in nodos_info:
            n_id = info['id']
            es_prima = info['es_prima']
            self.nodos[n_id] = NodoPrima(id=n_id) if es_prima else Nodo(id=n_id)

    def mover(self, nodo_id: int, agente_id: int) -> None:
        """Mueve un agente hacia el nodo dado, si el movimiento es válido."""
        agente = self.agentes[agente_id]
        nodo = self.nodos[nodo_id]
        agente.posicion.mover_agente(nodo)

    def conectar_nodos(self, conexiones: Iterable[list[int] | tuple[int, int]]) -> None:
        """Conecta pares de nodos existentes."""
        for con in conexiones:
            n_1 = con[0]
            n_2 = con[1]
            if n_1 not in self.nodos or n_2 not in self.nodos:
                raise Exception('Se intenta conectar nodos inexistentes.')
            self.nodos[n_1].conectar(self.nodos[n_2])

    def cargar_agentes(self, agente_info: Iterable[AgenteInfo]) -> None:
        """Crea los agentes y los ubica en su nodo inicial."""
        for info in agente_info:
            a_id = info['id']
            n_id = info['nodo_inicio']
            if n_id not in self.nodos:
                raise Exception(f'El nodo de inicio {n_id} no existe.')
            agente = Agente(id=a_id, nodo=self.nodos[n_id])
            self.agentes[a_id] = agente

    def estado_actual_to_dict(self) -> dict:
        """Serializa el estado actual del plano a un diccionario tipo init.json."""
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

        return {'nodos': nodos, 'conexiones': conexiones, 'agentes': agentes}

    def visualizar_plano(self, output_path: str | Path | None = None) -> Path:
        """Dibuja el plano actual (nodos, sombras y agentes) y lo guarda como PNG."""
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import networkx as nx

        vis = self.config['visualizacion']

        if output_path is None:
            output_path = Path(self.config['salida']['directorio']) / 'plano.png'
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

        posiciones = nx.spring_layout(grafo, seed=vis['seed_layout'])

        nodos_normales = [n for n in self.nodos.values() if not isinstance(n, NodoPrima)]
        nodos_primas = [n for n in self.nodos.values() if isinstance(n, NodoPrima)]
        nodos_sombra = [
            sombra
            for nodo in self.nodos.values()
            if isinstance(nodo, NodoPrima)
            for sombra in nodo.nodos_sombra
        ]

        fig, ax = plt.subplots(figsize=tuple(vis['figsize']))
        nx.draw_networkx_edges(grafo, posiciones, width=vis['ancho_arista'], alpha=vis['alpha_arista'], ax=ax)
        nx.draw_networkx_nodes(
            grafo, posiciones, nodelist=nodos_normales,
            node_color=vis['nodo_normal']['color'], node_size=vis['nodo_normal']['tamano'],
            edgecolors='black', linewidths=1, ax=ax,
        )
        nx.draw_networkx_nodes(
            grafo, posiciones, nodelist=nodos_primas,
            node_color=vis['nodo_prima']['color'], node_size=vis['nodo_prima']['tamano'],
            edgecolors='black', linewidths=1, ax=ax,
        )
        if nodos_sombra:
            nx.draw_networkx_nodes(
                grafo, posiciones, nodelist=nodos_sombra,
                node_color=vis['nodo_sombra']['color'], node_size=vis['nodo_sombra']['tamano'],
                edgecolors='black', linewidths=1, ax=ax,
            )

        labels = {
            nodo: str(nodo.id) if not hasattr(nodo, 'nodo_prima') else ''
            for nodo in grafo.nodes
        }
        nx.draw_networkx_labels(
            grafo, posiciones, labels=labels,
            font_size=vis['tamano_fuente'], font_color=vis['color_fuente'], ax=ax,
        )

        for agente in self.agentes.values():
            if agente.posicion not in posiciones:
                continue
            x, y = posiciones[agente.posicion]
            ax.text(
                x, y + 0.08, f'A{agente.id}', ha='center', va='center',
                fontsize=vis['tamano_fuente_etiqueta_agente'], fontweight='bold', color=vis['color_fuente'],
            )

        ax.set_title('Plano')
        ax.axis('off')
        fig.tight_layout()
        fig.savefig(output_path, dpi=vis['dpi'])
        plt.close(fig)
        return output_path

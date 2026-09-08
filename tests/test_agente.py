import pytest

from mapf.agente import Agente
from mapf.nodo import Nodo


def test_set_posicion_nodo_libre():
    nodo = Nodo(1)
    agente = Agente(id=1, nodo=nodo)
    assert agente.posicion is nodo
    assert nodo.agente is agente


def test_set_posicion_nodo_ocupado_no_prima_lanza_excepcion():
    nodo = Nodo(1)
    Agente(id=1, nodo=nodo)
    with pytest.raises(Exception):
        Agente(id=2, nodo=nodo)


def test_agente_eq_y_hash_por_id():
    agente_1 = Agente(id=1, nodo=Nodo(10))
    agente_1_bis = Agente(id=1, nodo=Nodo(11))
    agente_2 = Agente(id=2, nodo=Nodo(12))
    assert agente_1 == agente_1_bis
    assert agente_1 != agente_2
    assert hash(agente_1) == hash(agente_1_bis)

import pytest

from mapf.agente import Agente
from mapf.nodo import Nodo


def test_conectar_es_bidireccional():
    a = Nodo(1)
    b = Nodo(2)
    a.conectar(b)
    assert b in a.conexiones
    assert a in b.conexiones


def test_mover_a_nodo_no_adyacente_falla():
    a = Nodo(1)
    b = Nodo(2)
    Agente(id=1, nodo=a)
    with pytest.raises(Exception):
        a.mover_agente(b)


def test_mover_a_nodo_ocupado_no_prima_falla():
    a = Nodo(1)
    b = Nodo(2)
    a.conectar(b)
    Agente(id=1, nodo=a)
    Agente(id=2, nodo=b)
    with pytest.raises(Exception):
        a.mover_agente(b)


def test_mover_agente_exitoso():
    a = Nodo(1)
    b = Nodo(2)
    a.conectar(b)
    agente = Agente(id=1, nodo=a)
    a.mover_agente(b)
    assert a.agente is None
    assert b.agente is agente
    assert agente.posicion is b

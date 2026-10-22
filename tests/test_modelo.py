import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import modelo as m

EQ = "0.02*x**2 + 0.01*y**2 + 0.03*x*y"


@pytest.fixture
def funcs():
    return m.obtener_funciones(EQ)


def test_concentracion(funcs):
    f_c, *_ = funcs
    # 0.02*100 + 0.01*25 + 0.03*50 = 2 + 0.25 + 1.5
    assert math.isclose(m.concentracion(10, 5, f_c), 3.75)


def test_gradiente(funcs):
    _, f_gx, f_gy, *_ = funcs
    gx, gy = m.gradiente(10, 5, f_gx, f_gy)
    assert math.isclose(gx, 0.04 * 10 + 0.03 * 5)
    assert math.isclose(gy, 0.02 * 5 + 0.03 * 10)


def test_derivada_direccional_en_direccion_gradiente(funcs):
    _, f_gx, f_gy, *_ = funcs
    gx, gy = m.gradiente(10, 5, f_gx, f_gy)
    assert math.isclose(m.derivada_direccional(10, 5, gx, gy, f_gx, f_gy), math.hypot(gx, gy))


def test_derivada_direccional_reducir_emisiones(funcs):
    _, f_gx, f_gy, *_ = funcs
    gx, _ = m.gradiente(10, 5, f_gx, f_gy)
    assert math.isclose(m.derivada_direccional(10, 5, -1, 0, f_gx, f_gy), -gx)


def test_derivada_direccional_perpendicular_es_cero(funcs):
    _, f_gx, f_gy, *_ = funcs
    gx, gy = m.gradiente(10, 5, f_gx, f_gy)
    assert math.isclose(m.derivada_direccional(10, 5, -gy, gx, f_gx, f_gy), 0, abs_tol=1e-12)


def test_parser_acepta_sintaxis_informal():
    f1, *_ = m.obtener_funciones(EQ)
    f2, *_ = m.obtener_funciones("0.02x^2 + 0.01y^2 + 0.03xy")
    assert math.isclose(f1(10, 5), f2(10, 5))


def test_parser_rechaza_variables_extranas():
    with pytest.raises(ValueError):
        m.parsear_ecuacion("x + z")


def test_parser_rechaza_vacio_y_sintaxis_invalida():
    with pytest.raises(ValueError):
        m.parsear_ecuacion("")
    with pytest.raises(ValueError):
        m.parsear_ecuacion("x +")


def test_unitario_vector_cero():
    with pytest.raises(ValueError):
        m.unitario(0, 0)


def test_malla_constante_y_no_definida():
    f_c, *_ = m.obtener_funciones("5")
    xs, ys, Z = m.malla(50, 30, f_c, n=10)
    assert Z.shape == (10, 10) and np.all(Z == 5)

    f_c, *_ = m.obtener_funciones("log(x)")
    _, _, Z = m.malla(50, 30, f_c, n=10)
    assert np.isnan(Z[:, 0]).all()        # log(0) -> NaN, no inf
    assert np.isfinite(Z[:, 1:]).all()


def test_division_entre_cero_no_lanza_excepcion():
    # En x=20 la ecuación no está definida: debe dar inf/NaN, no reventar.
    f_c, f_gx, f_gy, *_ = m.obtener_funciones("1/(x-20)")
    assert not np.isfinite(m.concentracion(20, 5, f_c))
    gx, gy = m.gradiente(20, 5, f_gx, f_gy)
    assert not np.isfinite(gx) and math.isclose(gy, 0.0)
    assert math.isclose(m.concentracion(21, 5, f_c), 1.0)


def test_hessiana_y_clasificacion():
    cxx, cxy, cyy, D = m.hessiana_en(EQ, 10, 5)
    assert math.isclose(cxx, 0.04) and math.isclose(cxy, 0.03) and math.isclose(cyy, 0.02)
    assert D < 0 and m.clasificar_punto(cxx, cxy, cyy) == "punto silla"
    assert m.clasificar_punto(2, 0, 2) == "mínimo local"
    assert m.clasificar_punto(-2, 0, -2) == "máximo local"


def test_puntos_criticos():
    pcs = m.puntos_criticos("(x-10)**2 + (y-5)**2")
    assert len(pcs) == 1
    p = pcs[0]
    assert math.isclose(p["x"], 10) and math.isclose(p["y"], 5) and p["tipo"] == "mínimo local"
    assert m.puntos_criticos("x + y") == []


def test_plano_tangente():
    L = m.plano_tangente(EQ, 10, 5)
    # L(x,y) = 3.75 + 0.55(x-10) + 0.4(y-5)
    assert math.isclose(float(L.subs({m.x_sym: 10, m.y_sym: 5})), 3.75)
    assert math.isclose(float(L.subs({m.x_sym: 11, m.y_sym: 5})), 3.75 + 0.55)


def test_angulo_gradiente():
    assert math.isclose(m.angulo_gradiente(1, 0), 0)
    assert math.isclose(m.angulo_gradiente(0, 1), 90)
    assert math.isclose(m.angulo_gradiente(-1, 0), 180)

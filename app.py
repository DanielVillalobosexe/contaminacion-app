"""
app.py  -  Contaminación atmosférica: IA (Groq), Ecuaciones Dinámicas y Base de Datos
Ejecutar con:   streamlit run app.py
"""
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import sympy as sp
from sqlalchemy import select

import database as db
import ia_groq as ia
import modelo as m

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

st.set_page_config(page_title="Contaminación IA & Math", page_icon="🌫️", layout="wide")
st.title("🌫️ Contaminación Atmosférica con IA")

# ---------------------- FONDO BLANCO / FONDO NEGRO --------------------------
# El interruptor de la barra lateral cambia el tema de toda la app (fondo blanco
# o negro, con textos y gráficas coherentes). Streamlit lee el tema al iniciar
# cada ejecución, así que se aplica el cambio y se repinta una vez.
st.session_state.setdefault("fondo_negro", st._config.get_option("theme.base") == "dark")
st.session_state.setdefault("_fondo_aplicado", st.session_state["fondo_negro"])
if st.session_state["fondo_negro"] != st.session_state["_fondo_aplicado"]:
    st._config.set_option("theme.base", "dark" if st.session_state["fondo_negro"] else "light")
    st.session_state["_fondo_aplicado"] = st.session_state["fondo_negro"]
    st.rerun()

# ------------------------- CONFIGURACIÓN DE ECUACIÓN -------------------------
ECUACION_INICIAL = "0.02*x**2 + 0.01*y**2 + 0.03*x*y"

# Modelos típicos de contaminación que se pueden cargar con un toque
PLANTILLAS = {
    "Cuadrático (por defecto)": ECUACION_INICIAL,
    "Dilución por viento  C = x/(1+y)": "x/(1 + y)",
    "Decaimiento exponencial  C = x·e^(−0.1y)": "x*exp(-0.1*y)",
    "Dispersión gaussiana": "20*exp(-((x-25)^2)/200 - ((y-15)^2)/50)",
    "Fuente + viento cruzado": "0.05*x^2 - 0.4*x*y + 0.8*y^2",
}

# Teclas del teclado virtual: etiqueta -> texto que se inserta
TECLAS = {
    "x": "x", "y": "y",
    "7": "7", "8": "8", "9": "9",
    "4": "4", "5": "5", "6": "6",
    "1": "1", "2": "2", "3": "3",
    "0": "0", ".": ".",
    "+": " + ", "−": " - ", "×": "*", "÷": "/",
    "( ": "(", " )": ")",
    "x²": "x^2", "y²": "y^2", "x·y": "x*y", "^": "^",
    "√(": "sqrt(", "e^(": "exp(",
}


def _tecla_pulsada():
    """Callback del teclado: inserta la tecla elegida en la ecuación."""
    tecla = st.session_state.get("tecla")
    if tecla:
        st.session_state.ecuacion = (st.session_state.get("ecuacion", "") + TECLAS[tecla]).lstrip()
    st.session_state.tecla = None          # deselecciona para poder repetir la tecla


def _borrar_ultimo():
    st.session_state.ecuacion = st.session_state.get("ecuacion", "").rstrip()[:-1].rstrip()


def _limpiar():
    st.session_state.ecuacion = ""


def _cargar_plantilla():
    nombre = st.session_state.get("plantilla")
    if nombre:
        st.session_state.ecuacion = PLANTILLAS[nombre]


if "ecuacion" not in st.session_state:
    st.session_state.ecuacion = ECUACION_INICIAL

with st.expander("📝 Configurar Ecuación Matemática", expanded=True):
    st.text_input("Ecuación C(x, y)   (x = emisiones, y = viento)", key="ecuacion")

    st.caption("⌨️ Teclado matemático")
    st.pills("Teclado", options=list(TECLAS.keys()), selection_mode="single",
             key="tecla", on_change=_tecla_pulsada, label_visibility="collapsed")

    cb1, cb2, cb3 = st.columns([1, 1, 3])
    cb1.button("⌫ Borrar", on_click=_borrar_ultimo, width="stretch")
    cb2.button("🗑️ Limpiar", on_click=_limpiar, width="stretch")
    cb3.selectbox("📂 Cargar modelo de contaminación", options=list(PLANTILLAS.keys()),
                  index=None, placeholder="Elige un modelo…", key="plantilla",
                  on_change=_cargar_plantilla, label_visibility="collapsed")

    ecuacion_input = st.session_state.ecuacion
    try:
        expr = m.parsear_ecuacion(ecuacion_input)
        f_c, f_gx, f_gy, diff_x, diff_y = m.obtener_funciones(ecuacion_input)
        st.success(f"Ecuación cargada: $C(x, y) = {sp.latex(expr)}$")
    except Exception as e:
        st.error(f"Error en la ecuación: {e}")
        st.stop()

# ------------------------- ESCALA Y APARIENCIA (barra lateral) --------------
with st.sidebar:
    st.header("Escala de los ejes")
    xmax = st.number_input("Máximo del eje x (emisiones)", 10, 500, 50, step=10)
    ymax = st.number_input("Máximo del eje y (viento)", 10, 200, 30, step=5)

    st.header("Apariencia")
    st.toggle("Fondo negro", key="fondo_negro",
              help="Cambia el fondo de la app entre blanco y negro.")

# ------------ PUNTO DE ANÁLISIS Y DIRECCIÓN (panel principal) ---------------
with st.container(border=True):
    st.subheader("1️⃣ Punto de análisis")
    cp1, cp2 = st.columns(2)
    x = cp1.number_input("Emisiones (x)", 0.0, float(xmax), 20.0, 0.5,
                         help="Intensidad de emisiones en el eje x.")
    y = cp2.number_input("Viento (y)", 0.0, float(ymax), 10.0, 0.5,
                         help="Velocidad del viento en el eje y.")

    st.subheader("2️⃣ Dirección del vector")
    cd1, cd2 = st.columns(2)
    vx = cd1.number_input("Componente vx", value=1.0, step=0.25,
                          help="Componente de la dirección sobre el eje x (emisiones).")
    vy = cd2.number_input("Componente vy", value=1.0, step=0.25,
                          help="Componente de la dirección sobre el eje y (viento).")

    # El vector unitario se obtiene SIEMPRE con la misma fórmula fija: û = v/|v|.
    try:
        ux, uy = m.unitario(vx, vy)
    except ValueError as e:
        st.error(f"No se puede calcular el vector unitario: {e}")
        st.stop()
    st.caption(f"Vector unitario: û = v/|v| = ({ux:.4f}, {uy:.4f})")

# ------------------------------- CÁLCULOS ----------------------------------
c = m.concentracion(x, y, f_c)
gx, gy = m.gradiente(x, y, f_gx, f_gy)
mag = m.magnitud_gradiente(gx, gy)
ang_grad = m.angulo_gradiente(gx, gy)
dd = m.derivada_direccional(x, y, ux, uy, f_gx, f_gy)

if not all(map(lambda v: v == v and abs(v) != float("inf"), (c, gx, gy))):
    st.warning("La ecuación no está definida (o no es finita) en el punto actual. Mueve x o y.")

# ------------------------------- SALIDAS -----------------------------------
col1, col2, col3 = st.columns(3)
col1.metric("Concentración C(x, y)", f"{c:.4f}")
col2.metric("|∇C| (tasa máxima de cambio)", f"{mag:.4f}",
            help=f"Ángulo del gradiente: {ang_grad:.1f}°")
col3.metric("Derivada direccional D_u C", f"{dd:.4f}",
            delta="aumenta" if dd > 0 else ("disminuye" if dd < 0 else "sin cambio"),
            delta_color="inverse")

st.markdown("**Vector gradiente y vector unitario**")
st.dataframe(pd.DataFrame([
    {"Vector": "∇C (gradiente)",
     "Componentes": f"({gx:.4f}, {gy:.4f})",
     "Módulo": f"{mag:.4f}",
     "Ángulo": f"{ang_grad:.1f}°"},
    {"Vector": "û = v/|v| (unitario)",
     "Componentes": f"({ux:.4f}, {uy:.4f})",
     "Módulo": "1.0000",
     "Ángulo": f"{m.angulo_gradiente(ux, uy):.1f}°"},
]), hide_index=True)

with st.expander("🧮 Ver el procedimiento paso a paso"):
    st.markdown("**Paso 1 — Vector unitario (fórmula fija)**")
    st.latex(r"\hat{u}=\frac{\vec{v}}{\|\vec{v}\|}=\frac{(v_x,\,v_y)}"
             r"{\sqrt{v_x^{2}+v_y^{2}}}")
    st.latex(rf"\hat{{u}}=\frac{{({vx:g},\,{vy:g})}}"
             rf"{{\sqrt{{({vx:g})^{{2}}+({vy:g})^{{2}}}}}}=({ux:.4f},\,{uy:.4f})")

    st.markdown("**Paso 2 — Función y gradiente**")
    st.latex(rf"C(x,y)={sp.latex(expr)}")
    st.latex(rf"\nabla C=\left({sp.latex(diff_x)},\;{sp.latex(diff_y)}\right)")
    st.latex(rf"C({x:g},{y:g})={c:.4f}")
    st.latex(rf"\nabla C({x:g},{y:g})=({gx:.4f},\;{gy:.4f}),\qquad "
             rf"|\nabla C|={mag:.4f}\quad({ang_grad:.1f}^\circ)")

    st.markdown("**Paso 3 — Derivada direccional**")
    st.latex(r"D_{\hat{u}}C=\nabla C\cdot\hat{u}=C_x\,u_x+C_y\,u_y")
    st.latex(rf"D_{{\hat{{u}}}}C=({gx:.4f})({ux:.4f})+({gy:.4f})({uy:.4f})={dd:.4f}")

    st.caption("Recuerda: D_u C es máxima (= |∇C|) en la dirección de ∇C, mínima (= −|∇C|) en −∇C "
               "y cero en la dirección perpendicular (a lo largo de la curva de nivel).")

# --------------------- TABLA DE PUNTOS QUE SE AGREGAN ----------------------
with st.expander("📌 Agregar puntos y compararlos", expanded=True):
    st.caption("Agrega las filas que quieras: en cada punto se calculan el gradiente ∇C, "
               "el vector unitario û y la derivada direccional D_u C con la dirección de arriba.")
    puntos = st.data_editor(
        pd.DataFrame({"x": [20.0, 5.0], "y": [10.0, 25.0]}),
        num_rows="dynamic", key="puntos", width="stretch",
        column_config={
            "x": st.column_config.NumberColumn("Emisiones (x)", step=0.5, format="%.3f"),
            "y": st.column_config.NumberColumn("Viento (y)", step=0.5, format="%.3f"),
        },
    )

    filas = []
    for _, fila in puntos.dropna().iterrows():
        px, py = float(fila["x"]), float(fila["y"])
        pgx, pgy = m.gradiente(px, py, f_gx, f_gy)
        pdd = m.derivada_direccional(px, py, ux, uy, f_gx, f_gy)
        filas.append({
            "x": px, "y": py,
            "C(x,y)": m.concentracion(px, py, f_c),
            "∇C": f"({pgx:.4f}, {pgy:.4f})",
            "|∇C|": m.magnitud_gradiente(pgx, pgy),
            "û": f"({ux:.4f}, {uy:.4f})",
            "D_u C": pdd,
            "cambio": "aumenta" if pdd > 0 else ("disminuye" if pdd < 0 else "sin cambio"),
        })

    if filas:
        st.dataframe(pd.DataFrame(filas), hide_index=True)
    else:
        st.info("Agrega al menos un punto (x, y) para ver sus resultados.")


# ------------------------ ANÁLISIS DE SEGUNDO ORDEN -------------------------
with st.expander("🔬 Análisis avanzado: Hessiana, puntos críticos y plano tangente"):
    try:
        H = m.hessiana(ecuacion_input)
        cxx, cxy, cyy, detH = m.hessiana_en(ecuacion_input, x, y)
        st.markdown("**Matriz Hessiana**")
        st.latex(rf"H = {sp.latex(H)}")
        st.latex(rf"H({x:g},{y:g}) = \begin{{pmatrix}} {cxx:.4f} & {cxy:.4f} \\ {cxy:.4f} & {cyy:.4f} \end{{pmatrix}},"
                 rf"\qquad D = C_{{xx}}C_{{yy}}-C_{{xy}}^2 = {detH:.6f}")

        st.markdown("**Puntos críticos (∇C = 0)**")
        pcs = m.puntos_criticos(ecuacion_input)
        if pcs:
            st.dataframe(pd.DataFrame(pcs).rename(columns={"tipo": "clasificación"}), hide_index=True)
        else:
            st.info("No hay puntos críticos aislados (o SymPy no pudo resolver el sistema).")

        st.markdown("**Plano tangente / linealización en el punto actual**")
        L = m.plano_tangente(ecuacion_input, x, y)
        st.latex(rf"L(x,y) = {sp.latex(L)}")
        dx_ = st.number_input("Δx", value=1.0, step=0.5, key="dx")
        dy_ = st.number_input("Δy", value=1.0, step=0.5, key="dy")
        est = m.aproximacion_lineal(x, y, c, gx, gy, dx_, dy_)
        real = m.concentracion(x + dx_, y + dy_, f_c) - c
        st.latex(rf"\Delta C \approx C_x\,\Delta x + C_y\,\Delta y = ({gx:.4f})({dx_:g})+({gy:.4f})({dy_:g}) = {est:.4f}")
        st.caption(f"Cambio real: ΔC = {real:.4f}  →  error de la aproximación lineal: {abs(real - est):.4f}")
        analisis_extra = {
            "Hessiana en el punto": f"Cxx={cxx:.4f}, Cxy={cxy:.4f}, Cyy={cyy:.4f}, D={detH:.6f}",
            "Puntos críticos": "; ".join(f"({p['x']:.3g}, {p['y']:.3g}) C={p['C']:.3g} {p['tipo']}" for p in pcs) or "ninguno",
            "Plano tangente": str(L),
            "Ángulo del gradiente": f"{ang_grad:.1f}°",
        }
    except Exception as e:
        st.warning(f"No se pudo completar el análisis avanzado: {e}")
        analisis_extra = None

# ----------------------------- VISUALIZACIÓN --------------------------------
tab2d, tab3d, tabia, tabreportes = st.tabs(
    ["🗺️ Mapa 2D", "🏔️ Superficie 3D", "🤖 Asistente IA", "📊 Reportes & Historial"])

xs, ys, Z = m.malla(xmax, ymax, f_c)

with tab2d:
    niveles = st.slider("Número de curvas de nivel", 3, 25, 10)
    ver_flechas = st.checkbox("Mostrar vectores de gradiente", True)

    fig = go.Figure()
    fig.add_trace(go.Heatmap(x=xs, y=ys, z=Z, colorscale="YlOrRd", colorbar=dict(title="C(x,y)")))
    fig.add_trace(go.Contour(x=xs, y=ys, z=Z, ncontours=niveles, showscale=False,
                             contours=dict(coloring="none", showlabels=True),
                             line=dict(color="black", width=1), name="Curvas de nivel"))
    if ver_flechas:
        fx, fy = m.flechas_gradiente(xmax, ymax, f_gx, f_gy)
        fig.add_trace(go.Scatter(x=fx, y=fy, mode="lines",
                                 line=dict(color="royalblue", width=2), name="∇C"))
    fig.add_trace(go.Scatter(x=[x], y=[y], mode="markers",
                             marker=dict(size=12, color="white", line=dict(color="black", width=2)),
                             name="Punto actual"))
    if filas:
        fig.add_trace(go.Scatter(
            x=[f["x"] for f in filas], y=[f["y"] for f in filas],
            mode="markers", name="Puntos añadidos",
            marker=dict(size=10, color="deepskyblue", symbol="diamond",
                        line=dict(color="black", width=1))))

    # Dos flechas sobre el punto actual: la dirección û (verde) y el gradiente ∇C (azul).
    largo = 0.12
    fig.add_annotation(x=x + ux * largo * xmax, y=y + uy * largo * ymax, ax=x, ay=y,
                       xref="x", yref="y", axref="x", ayref="y",
                       showarrow=True, arrowhead=3, arrowwidth=3, arrowcolor="green")
    if mag > 1e-12:
        fig.add_annotation(x=x + gx / mag * largo * xmax, y=y + gy / mag * largo * ymax,
                           ax=x, ay=y, xref="x", yref="y", axref="x", ayref="y",
                           showarrow=True, arrowhead=3, arrowwidth=3, arrowcolor="royalblue")
    fig.update_layout(xaxis_title="Emisiones (x)", yaxis_title="Viento (y)",
                      height=600, legend=dict(orientation="h", y=-0.15))
    st.plotly_chart(fig, width="stretch")
    st.caption("Flecha verde: dirección û que escribiste. Flecha azul: gradiente ∇C "
               "(la dirección en la que C crece más rápido; siempre perpendicular a la curva de nivel).")

with tab3d:
    fig3 = go.Figure(go.Surface(x=xs, y=ys, z=Z, colorscale="YlOrRd"))
    fig3.add_trace(go.Scatter3d(x=[x], y=[y], z=[c], mode="markers",
                                marker=dict(size=6, color="blue"), name="Punto actual"))
    fig3.update_layout(height=650, scene=dict(xaxis_title="Emisiones (x)",
                                              yaxis_title="Viento (y)", zaxis_title="C(x,y)"))
    st.plotly_chart(fig3, width="stretch")

# ------------------------------ ASISTENTE IA --------------------------------
with tabia:
    st.subheader("Pregúntale a la IA  🗣️ EL cordi")
    st.caption("Puedes preguntar sobre la app, sobre matemáticas o sobre cualquier otro tema.")
    
    # La clave se lee de GROQ_API_KEY: en local desde el archivo .env y en
    # Streamlit Cloud desde los "Secrets" de la app (nunca escrita en el código).
    clave = os.getenv("GROQ_API_KEY", "")
    if not clave:
        try:
            clave = st.secrets.get("GROQ_API_KEY", "")
        except Exception:
            clave = ""
    if not clave:
        clave = st.text_input("Pega tu API key de Groq (gsk_...)", type="password")


    contexto = ia.construir_contexto(
        ecuacion_input, x, y, c, gx, gy,
        f"vector escrito v = ({vx:g}, {vy:g})", ux, uy, dd,
        extra=analisis_extra)

    if "chat" not in st.session_state:
        st.session_state.chat = []     # lista de (pregunta, respuesta) de esta sesión

    with st.expander("📜 Ver historial guardado en la base de datos"):
        for h in db.obtener_historial_ia(10):
            st.markdown(f"**Tú:** {h.pregunta}")
            st.markdown(f"**IA:** {h.respuesta}")
            st.divider()

    for p, r in st.session_state.chat:
        with st.chat_message("user"):
            st.markdown(p)
        with st.chat_message("assistant"):
            st.markdown(r)

    pregunta = st.chat_input("¿En qué puedo ayudarte?")
    if pregunta and pregunta.strip():
        with st.chat_message("user"):
            st.markdown(pregunta)
        with st.chat_message("assistant"):
            caja = st.empty()
            historial = list(reversed(db.obtener_historial_ia(6)))   # del más antiguo al más reciente
            respuesta = ia.preguntar(pregunta, contexto, api_key=clave, historial=historial,
                                     stream_callback=lambda t: caja.markdown(t + "▌"))
            caja.markdown(respuesta)
        st.session_state.chat.append((pregunta, respuesta))
        db.guardar_historial_ia(pregunta, respuesta, contexto)

    if st.button("🗑️ Limpiar chat de esta sesión"):
        st.session_state.chat = []
        st.rerun()

# ------------------------------- REPORTES ----------------------------------
with tabreportes:
    st.subheader("📝 Generar Reporte")
    comentario = st.text_area("Notas adicionales para el reporte:")
    if st.button("Guardar Reporte Actual"):
        db.guardar_reporte(ecuacion_input, x, y, c, comentario)
        st.success("Reporte guardado en la base de datos.")

    st.divider()
    st.subheader("📋 Últimos Reportes")
    with db.engine.connect() as conn:
        df = pd.read_sql(select(db.Reporte).order_by(db.Reporte.fecha.desc()).limit(10), conn)
    if not df.empty:
        st.dataframe(df, hide_index=True)
    else:
        st.info("No hay reportes guardados aún.")

# 🌫️ Contaminación atmosférica — Gradiente y derivada direccional

Modelo por defecto: C(x, y) = 0.02x² + 0.01y² + 0.03xy  (x = emisiones, y = viento).
La ecuación se puede cambiar desde la app (acepta `^`, `2x`, `sin`, `cos`, `exp`, `log`, `sqrt`).

## Qué calcula
- Concentración C(x, y), derivadas parciales y gradiente ∇C (|∇C| y su ángulo).
- Derivada direccional D_u C en direcciones predefinidas (±x, ±y, ±∇C, curva de nivel) o ángulo libre.
- Matriz Hessiana, puntos críticos (∇C = 0) con clasificación (mínimo / máximo / silla).
- Plano tangente (linealización) y estimación ΔC ≈ Cx·Δx + Cy·Δy con su error real.
- Mapa 2D (calor + curvas de nivel + campo de gradiente) y superficie 3D.
- Asistente IA (Groq, API compatible con OpenAI) con el contexto de la app; responde cualquier tema.
- Reportes e historial de chat en SQLite.

## Estructura
```
contaminacion_app/
├── app.py              # App Streamlit (Python + Plotly + Groq)
├── modelo.py           # Matemáticas: C, gradiente, derivada direccional, Hessiana, puntos críticos
├── ia_groq.py          # Conexión con la API de Groq
├── database.py         # SQLite (reportes + historial IA)
├── requirements.txt    # Dependencias
├── .env.example        # Plantilla para tu API key (copiar a .env)
├── tests/test_modelo.py
└── web/                # Versión HTML + CSS + JavaScript (Plotly.js + Chart.js)
```

## Ejecutar la versión Streamlit
```
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # Windows: copy   -> pega tu GROQ_API_KEY
streamlit run app.py
```
Si ya usas Anaconda: `~/anaconda3/bin/pip install -r requirements.txt` y `~/anaconda3/bin/streamlit run app.py`.

**Nunca escribas la API key en el código**: va en `.env`, que está en `.gitignore`.
En Streamlit Cloud se pone en *Settings → Secrets* como `GROQ_API_KEY = "gsk_..."`.

## Ejecutar la versión web
Abre `web/index.html` en el navegador (necesita internet para cargar Plotly y Chart.js).

## Pruebas
```
pytest
```

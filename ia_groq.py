"""
ia_groq.py
Conexión con la API de Groq para el asistente de la app.

La clave se lee de la variable de entorno GROQ_API_KEY (archivo .env).
Nunca escribas la clave directamente en este archivo.
"""
import os

try:
    import openai
except ImportError:  # pragma: no cover
    openai = None

# Groq expone una API compatible con la de OpenAI; solo cambia la dirección.
URL_BASE = "https://api.groq.com/openai/v1"
MODELO_POR_DEFECTO = "openai/gpt-oss-120b"

SYSTEM_PROMPT = """Eres un asistente general integrado en una app de Streamlit sobre
contaminación atmosférica (gradiente y derivada direccional).

Reglas:
- Responde en español, de forma clara y directa.
- Puedes responder sobre CUALQUIER tema: matemáticas, programación, ciencia,
  cultura general, redacción, etc. No te limites solo a la contaminación.
  No digas que "solo puedes ayudar con la app"; si la pregunta no tiene que
  ver con la app, simplemente respóndela.
- Cuando la pregunta sí trate de la app, usa el CONTEXTO que se te da
  (ecuación, punto actual, gradiente, derivada direccional) para explicar
  los cálculos paso a paso. Usa LaTeX con $...$ para fórmulas.
- Si no sabes algo, dilo; no inventes datos.
"""


def construir_contexto(ecuacion, x, y, c, gx, gy, nombre_dir, ux, uy, dd,
                       extra=None):
    """Arma el texto de contexto con el estado actual de la app."""
    mag = (gx ** 2 + gy ** 2) ** 0.5
    texto = (
        "CONTEXTO ACTUAL DE LA APP\n"
        f"- Ecuación: C(x, y) = {ecuacion}\n"
        "  (x = intensidad de emisiones, y = velocidad del viento)\n"
        f"- Punto actual: x = {x:g}, y = {y:g}\n"
        f"- Concentración: C = {c:.4f}\n"
        f"- Gradiente: ∇C = ({gx:.4f}, {gy:.4f}), |∇C| = {mag:.4f}\n"
        f"- Dirección elegida: {nombre_dir}, û = ({ux:.3f}, {uy:.3f})\n"
        f"- Derivada direccional: D_u C = {dd:.4f} "
        f"({'aumenta' if dd > 0 else 'disminuye' if dd < 0 else 'no cambia'})\n"
    )
    if extra:
        texto += "\nANÁLISIS ADICIONAL\n"
        for k, v in extra.items():
            texto += f"- {k}: {v}\n"
    return texto


def _mensajes(pregunta, contexto, historial):
    """Construye la lista de mensajes (historial + pregunta actual)."""
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in historial or []:
        if getattr(h, "pregunta", None) and getattr(h, "respuesta", None):
            msgs.append({"role": "user", "content": h.pregunta})
            msgs.append({"role": "assistant", "content": h.respuesta})
    msgs.append({
        "role": "user",
        "content": f"{contexto}\n\nPREGUNTA DEL USUARIO:\n{pregunta}",
    })
    return msgs


def preguntar(pregunta, contexto="", api_key=None, historial=None,
              modelo=None, max_tokens=5600, stream_callback=None):
    """
    Envía la pregunta a Groq y devuelve la respuesta como texto.

    - historial: iterable de objetos con atributos .pregunta y .respuesta,
      ordenados del más antiguo al más reciente.
    - stream_callback: función opcional que recibe cada fragmento de texto
      conforme llega (para mostrar la respuesta en tiempo real).
    """
    if openai is None:
        return "Falta la librería `openai`. Instálala con: pip install openai"

    clave = api_key or os.getenv("GROQ_API_KEY")
    if not clave:
        return "No hay API key. Define GROQ_API_KEY en el archivo .env."

    modelo = modelo or os.getenv("GROQ_MODEL") or MODELO_POR_DEFECTO
    cliente = openai.OpenAI(api_key=clave, base_url=URL_BASE)
    mensajes = _mensajes(pregunta, contexto, historial)

    try:
        if stream_callback is None:
            resp = cliente.chat.completions.create(
                model=modelo, max_tokens=max_tokens, messages=mensajes)
            return resp.choices[0].message.content or "La IA no devolvió texto."

        partes = []
        for trozo in cliente.chat.completions.create(
                model=modelo, max_tokens=max_tokens, messages=mensajes, stream=True):
            if not trozo.choices:
                continue
            texto = trozo.choices[0].delta.content
            if texto:
                partes.append(texto)
                stream_callback("".join(partes))
        return "".join(partes) or "La IA no devolvió texto."

    except openai.AuthenticationError:
        return "API key inválida. Revisa GROQ_API_KEY en .env."
    except openai.PermissionDeniedError:
        return "La clave no tiene permiso para este modelo de Groq."
    except openai.RateLimitError:
        return "Límite de uso alcanzado. Espera un momento e inténtalo de nuevo."
    except openai.NotFoundError:
        return f"El modelo «{modelo}» no existe en Groq. Revisa GROQ_MODEL en .env."
    except openai.APIStatusError as e:
        return f"Error de la API de Groq ({e.status_code}): {e.message}"
    except openai.APIConnectionError:
        return "No se pudo conectar con Groq. Revisa tu conexión a internet."
    except Exception as e:  # cualquier otro fallo inesperado
        return f"Error inesperado al consultar la IA: {e}"

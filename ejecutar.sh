#!/usr/bin/env bash
# Arranca la app y muestra la dirección para abrirla desde el celular.
# Uso:  ./ejecutar.sh
cd "$(dirname "$0")"

# Usa el Python de Anaconda si existe; si no, el del sistema / venv activo
if [ -x "$HOME/anaconda3/bin/streamlit" ]; then
  STREAMLIT="$HOME/anaconda3/bin/streamlit"
else
  STREAMLIT="streamlit"
fi

IP=$(hostname -I 2>/dev/null | awk '{print $1}')
PUERTO=8501

echo "============================================================"
echo "  Contaminación IA & Math"
echo "  En esta PC:        http://localhost:$PUERTO"
if [ -n "$IP" ]; then
  echo "  En el celular:     http://$IP:$PUERTO   (misma red WiFi)"
else
  echo "  En el celular:     http://<IP-de-esta-PC>:$PUERTO"
fi
echo "  Ctrl+C para detener"
echo "============================================================"

exec "$STREAMLIT" run app.py --server.port "$PUERTO"

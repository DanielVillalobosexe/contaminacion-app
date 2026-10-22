/* =========================================================
   script.js - misma lógica que modelo.py, pero en el navegador
   ========================================================= */

// ---------- 1) MODELO MATEMÁTICO (edita los coeficientes aquí) ----------
const COEF = { A: 0.02, B: 0.01, D: 0.03 };
const XMAX = 50;   // rango del eje x (emisiones)
const YMAX = 30;   // rango del eje y (viento)

const C  = (x, y) => COEF.A * x * x + COEF.B * y * y + COEF.D * x * y;
const Cx = (x, y) => 2 * COEF.A * x + COEF.D * y;
const Cy = (x, y) => 2 * COEF.B * y + COEF.D * x;
const norm = (a, b) => Math.hypot(a, b);

function unitario(ux, uy) {
  const n = norm(ux, uy);
  return n === 0 ? [0, 0] : [ux / n, uy / n];
}

function direccion(tipo, x, y, angulo) {
  const gx = Cx(x, y), gy = Cy(x, y);
  switch (tipo) {
    case "menosX": return [-1, 0];
    case "masX": return [1, 0];
    case "menosY": return [0, -1];
    case "masY": return [0, 1];
    case "masGrad": return unitario(gx, gy);
    case "menosGrad": return unitario(-gx, -gy);
    default: {
      const r = (angulo * Math.PI) / 180;
      return [Math.cos(r), Math.sin(r)];
    }
  }
}

// ---------- 2) ELEMENTOS DE LA PÁGINA ----------
const $ = (id) => document.getElementById(id);
const sliderX = $("sliderX"), numX = $("numX"), outX = $("outX");
const sliderY = $("sliderY"), numY = $("numY"), outY = $("outY");
const selDir = $("direccion"), angulo = $("angulo");

let ultimoContexto = "";
let grafico = null; // instancia de Chart.js

// ---------- 3) MALLA Y FLECHAS ----------
const N = 60;
const xs = Array.from({ length: N }, (_, i) => (XMAX * i) / (N - 1));
const ys = Array.from({ length: N }, (_, i) => (YMAX * i) / (N - 1));
const Z = ys.map((yy) => xs.map((xx) => C(xx, yy)));

function flechas(paso = 6, largo = 0.06) {
  const fx = [], fy = [];
  for (let i = 1; i <= paso; i++) {
    for (let j = 1; j <= paso; j++) {
      const px = (XMAX * i) / (paso + 1), py = (YMAX * j) / (paso + 1);
      const dx = Cx(px, py) / XMAX, dy = Cy(px, py) / YMAX;
      const n = norm(dx, dy);
      if (n === 0) continue;
      const ux = dx / n, uy = dy / n;
      const x0 = px / XMAX, y0 = py / YMAX;
      const x1 = x0 + ux * largo, y1 = y0 + uy * largo;
      const seg = [[x0, y0], [x1, y1]];
      fx.push(x0 * XMAX, x1 * XMAX, null);
      fy.push(y0 * YMAX, y1 * YMAX, null);
      for (const a of [(150 * Math.PI) / 180, (-150 * Math.PI) / 180]) {
        const c = Math.cos(a), s = Math.sin(a), h = largo * 0.35;
        const hx = x1 + h * (ux * c - uy * s), hy = y1 + h * (ux * s + uy * c);
        fx.push(x1 * XMAX, hx * XMAX, null);
        fy.push(y1 * YMAX, hy * YMAX, null);
      }
    }
  }
  return [fx, fy];
}
const [FLECHAS_X, FLECHAS_Y] = flechas();

// ---------- 4) ACTUALIZAR TODO ----------
function actualizar() {
  const x = parseFloat(numX.value), y = parseFloat(numY.value);
  const ang = parseFloat(angulo.value);
  outX.textContent = x; outY.textContent = y; $("outAng").textContent = ang;
  $("bloqueAngulo").hidden = selDir.value !== "angulo";

  const c = C(x, y), gx = Cx(x, y), gy = Cy(x, y);
  const [ux, uy] = direccion(selDir.value, x, y, ang);
  const dd = gx * ux + gy * uy;

  $("resC").textContent = c.toFixed(4);
  $("resCx").textContent = gx.toFixed(4);
  $("resCy").textContent = gy.toFixed(4);
  $("resNorma").textContent = norm(gx, gy).toFixed(4);
  $("resU").textContent = `(${ux.toFixed(3)}, ${uy.toFixed(3)})`;
  $("resDD").textContent = dd.toFixed(4);
  $("interpretacion").textContent =
    dd > 0 ? "📈 En esa dirección la concentración AUMENTA."
    : dd < 0 ? "📉 En esa dirección la concentración DISMINUYE."
    : "➖ En esa dirección la concentración no cambia (instantáneamente).";

  ultimoContexto =
    `Modelo: C(x,y)=0.02x²+0.01y²+0.03xy (x emisiones, y viento).\n` +
    `Punto: x=${x}, y=${y}\nC=${c.toFixed(4)}\n∇C=(${gx.toFixed(4)}, ${gy.toFixed(4)})\n` +
    `Dirección u=(${ux.toFixed(3)}, ${uy.toFixed(3)})\nD_u C=${dd.toFixed(4)}\n`;

  dibujarMapa(x, y, ux, uy);
  dibujarPerfil(x, y, ux, uy);
}

function dibujarMapa(x, y, ux, uy) {
  const L = 0.12;
  const datos = [
    { type: "heatmap", x: xs, y: ys, z: Z, colorscale: "YlOrRd", colorbar: { title: "C" } },
    { type: "contour", x: xs, y: ys, z: Z, ncontours: 10, showscale: false,
      contours: { coloring: "none", showlabels: true }, line: { color: "black", width: 1 },
      name: "Curvas de nivel" },
    { type: "scatter", mode: "lines", x: FLECHAS_X, y: FLECHAS_Y,
      line: { color: "royalblue", width: 2 }, name: "∇C" },
    { type: "scatter", mode: "markers", x: [x], y: [y],
      marker: { size: 12, color: "white", line: { color: "black", width: 2 } }, name: "Punto" },
  ];
  const layout = {
    xaxis: { title: "Emisiones (x)" }, yaxis: { title: "Viento (y)" },
    margin: { t: 10 }, legend: { orientation: "h", y: -0.2 },
    annotations: [{ x: x + ux * L * XMAX, y: y + uy * L * YMAX, ax: x, ay: y,
      xref: "x", yref: "y", axref: "x", ayref: "y",
      showarrow: true, arrowhead: 3, arrowwidth: 3, arrowcolor: "green" }],
  };
  Plotly.react("mapa", datos, layout, { responsive: true });

  Plotly.react("superficie", [
    { type: "surface", x: xs, y: ys, z: Z, colorscale: "YlOrRd" },
    { type: "scatter3d", mode: "markers", x: [x], y: [y], z: [C(x, y)],
      marker: { size: 5, color: "blue" }, name: "Punto" },
  ], { margin: { t: 10 },
       scene: { xaxis: { title: "Emisiones (x)" }, yaxis: { title: "Viento (y)" }, zaxis: { title: "C" } } },
  { responsive: true });
}

function dibujarPerfil(x, y, ux, uy) {
  // C(x + t·ux, y + t·uy) para t entre -10 y 10
  const ts = Array.from({ length: 41 }, (_, i) => -10 + i * 0.5);
  const vals = ts.map((t) => C(x + t * ux, y + t * uy));
  if (grafico) grafico.destroy();
  grafico = new Chart($("perfil"), {
    type: "line",
    data: { labels: ts, datasets: [{ label: "C a lo largo de la dirección", data: vals,
      borderColor: "#d9480f", tension: 0.25, pointRadius: 0 }] },
    options: { scales: { x: { title: { display: true, text: "t (distancia desde el punto)" } },
                         y: { title: { display: true, text: "C" } } } },
  });
}

// ---------- 5) EVENTOS ----------
function enlazar(slider, num) {
  slider.addEventListener("input", () => { num.value = slider.value; actualizar(); });
  num.addEventListener("input", () => { slider.value = num.value; actualizar(); });
}
enlazar(sliderX, numX);
enlazar(sliderY, numY);
selDir.addEventListener("change", actualizar);
angulo.addEventListener("input", actualizar);

// ---------- 6) GEMINI (solo pruebas locales) ----------
const MODELO_GEMINI = "gemini-2.5-flash";
$("btnIA").addEventListener("click", async () => {
  const key = $("apiKey").value.trim();
  const salida = $("respuestaIA");
  if (!key) { salida.textContent = "⚠️ Pega primero tu API key."; return; }
  $("btnIA").disabled = true; salida.textContent = "Consultando a Gemini...";
  try {
    const r = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${MODELO_GEMINI}:generateContent`,
      { method: "POST",
        headers: { "Content-Type": "application/json", "x-goog-api-key": key },
        body: JSON.stringify({
          systemInstruction: { parts: [{ text: "Eres experto en cálculo multivariable. Responde en español, breve y claro." }] },
          contents: [{ parts: [{ text: ultimoContexto + "\nPregunta: " + $("pregunta").value }] }],
        }) });
    const j = await r.json();
    salida.textContent = j.candidates?.[0]?.content?.parts?.[0]?.text ?? JSON.stringify(j, null, 2);
  } catch (e) { salida.textContent = "⚠️ Error: " + e.message; }
  $("btnIA").disabled = false;
});

actualizar();

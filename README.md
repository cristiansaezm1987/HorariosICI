# 📊 Visualización Docente UA

> Sistema de visualización e información en tiempo real de la planificación académica — **Universidad Autónoma de Chile**

---

## 📌 Descripción

Plataforma web interactiva que permite visualizar, filtrar y analizar la distribución de la planificación académica universitaria: docentes, asignaturas, salas, horarios, cargas horarias y estadísticas institucionales.

### Funcionalidades principales
- **Dashboard general** con métricas institucionales, gráficos de distribución de contratos, jerarquía académica y grados académicos
- **Horarios por docente** con grilla semanal de 14 bloques académicos y badges por tipo de clase (TEO / AYU / LAB)
- **Horarios por nivel / sección** con información del docente asignado
- **Disponibilidad de salas** en tiempo real con calendario semanal
- **Vista de asignaturas (NRC)** con filtros avanzados y contabilidad de horas y créditos
- **Carga de planificación** vía archivo CSV (actualización dinámica de la base de datos)
- **Exportación a PDF** de horarios individuales

---

## 🛠️ Stack Tecnológico

| Capa | Tecnología |
|------|------------|
| Backend | Python · Flask · SQLite |
| Frontend | HTML5 · Vanilla CSS · Vanilla JavaScript |
| Gráficos | Chart.js |
| Íconos | Font Awesome |
| Fuentes | Google Fonts (Inter) |

---

## 📐 Estructura del Proyecto

```
visualizacion_docente_ua/
├── app.py              # API REST (Flask)
├── static/
│   ├── index.html      # SPA principal
│   ├── script.js       # Lógica frontend
│   └── styles.css      # Estilos y diseño
└── README.md
```

---

## 🚀 Uso

1. Instalar dependencias:
   ```bash
   pip install flask
   ```
2. Ejecutar la aplicación:
   ```bash
   python app.py
   ```
3. Abrir en el navegador: `http://localhost:5000`
4. Cargar un archivo CSV de planificación desde la interfaz.

---

## 📜 Licencia

**Herramienta de uso libre** para la comunidad académica de la **Universidad Autónoma de Chile**.  
Queda autorizado su uso, adaptación y distribución con fines educativos e institucionales, siempre que se mantengan los créditos de autoría.

---

## 👤 Créditos

<table>
  <tr>
    <td align="center" width="50%">
      <strong>Diseño, desarrollo e implementación</strong><br><br>
      <b>Héctor Orellana Rojas</b><br>
      Universidad Autónoma de Chile<br>
      <sub>Concepción, Chile · 2025</sub>
    </td>
    <td align="center" width="50%">
      <strong>Desarrollado con asistencia de IA</strong><br><br>
      <b>Antigravity · Google DeepMind</b><br>
      Agente de IA para programación asistida<br>
      <sub>Powered by Gemini</sub>
    </td>
  </tr>
</table>

---

<p align="center">
  <sub>© 2025 — Universidad Autónoma de Chile · Todos los derechos reservados</sub>
</p>

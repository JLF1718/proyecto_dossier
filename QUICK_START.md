# ⚡ Referencia Rápida

## 🎯 3 Formas de Usar el Proyecto

### 1️⃣ Opción Web (RECOMENDADO)
```bash
streamlit run app_ingreso_datos.py
```
✅ Interfaz visual  
✅ Ingresa datos fácilmente  
✅ Edita inline  
✅ Genera reportes con botón  

### 2️⃣ Opción CLI (Dashboards)
```bash
python generar_todos_dashboards.py S186
```
✅ Genera 3 reportes HTML  
✅ Rápido y directo  
✅ Para programación automática  

### 3️⃣ Opción Validación
```bash
python validar_proyecto.py
```
✅ Verifica todo funciona  
✅ 5 checks automáticos  
✅ Identifica problemas  

---

## 📋 Qué Hay en la App

```
🔴 CONTRATISTA: [BAYSA ▼] o JAMAR

🔴 ORIGEN: [Normalizado ○] o Fuente

📊 RESUMEN EJECUTIVO
   Total: 191
   Liberados: 100
   Observados: 70
   En Revisión: 2
   Planeados: 19

📅 PRÓXIMAS ENTREGAS (BAYSA)
   | Entrega | Planeados | Peso |
   |---------|-----------|------|
   | ENT001  |     5     | 1.20 |
   | ENT002  |     3     | 0.85 |
   | TOTAL   |   191     | 6.85 |

✏️ EDITOR INLINE
   [Click para editar cualquier celda]

🔵 [Agregar Nueva Fila]
🟢 [Generar Dashboards]
```

---

## 🐍 Comandos Útiles

| Comando | Efecto |
|---------|--------|
| `streamlit run app_ingreso_datos.py` | Abre app web |
| `python validar_proyecto.py` | Valida proyecto |
| `python estado_proyecto.py` | Status rápido |
| `python scripts/normalizar_baysa.py` | Regenera BAYSA |
| `python scripts/normalizar_jamar.py` | Regenera JAMAR |

---

## 📁 Archivos Importantes

| Archivo | Para |
|---------|------|
| `app_ingreso_datos.py` | 🌐 App web |
| `validar_proyecto.py` | ✅ Validación |
| `config.yaml` | 🎨 Estilos |
| `.streamlit/config.toml` | 🎨 Tema app |
| `README.md` | 📖 Documentación |

---

## 💾 Datos

```
BAYSA:    191 registros (activos)
JAMAR:    259 registros (activos)
Backup:   Automático en data/_backup/
```

---

## 🎨 Colores

```
Verde LIBERADO: #0F7C3F
(Tema ejecutivo limpio)
```

---

## ❓ Troubleshooting

### App no carga
```bash
# Ctrl+C en terminal
streamlit run app_ingreso_datos.py
```

### Datos no se ven
```bash
python validar_proyecto.py
# Revisa errores en salida
```

### Módulo no encontrado
```bash
pip install -r requirements.txt
```

---

## 📞 Documentación Completa

- [README.md](README.md) - Inicio
- [GUIA_RAPIDA.md](GUIA_RAPIDA.md) - Paso a paso
- [ARQUITECTURA.md](ARQUITECTURA.md) - Técnico

---

**¿Listo?** Ejecuta: `streamlit run app_ingreso_datos.py`

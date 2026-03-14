# Web App Profesional (Fase 1)

Portal de visualizacion en vivo para BAYSA y JAMAR, sin reemplazar Streamlit.

## Objetivo de Fase 1

- Interfaz web de solo lectura con estilo profesional.
- Datos en vivo desde los CSV actuales.
- API lista para futura migracion de formularios/edicion (Fase 2).

## Arranque local

1. Activar entorno virtual.
2. Instalar dependencias:

```bash
pip install -r requirements.txt
```

3. Ejecutar app web:

```bash
python cli.py run-web
```

4. Abrir en navegador:

- http://localhost:8000

## Enlace publico en vivo (Opcion 1)

Con la app corriendo en el puerto 8000:

```bash
cloudflared tunnel --url http://localhost:8000
```

Cloudflare mostrara una URL temporal similar a:

- https://algo-unico.trycloudflare.com

Comparte esa URL para visualizar el avance en vivo.

## Endpoints disponibles

- GET /api/health
- GET /api/summary
- GET /api/status-distribution
- GET /api/latest-rows?contractor=BAYSA&limit=12
- GET /api/latest-rows?contractor=JAMAR&limit=12

## Notas

- El frontend refresca automaticamente cada 15 segundos.
- Si detienes la app local o cierras el tunel, el enlace publico deja de funcionar.
- Esta fase no modifica tus flujos de generacion ni Streamlit.

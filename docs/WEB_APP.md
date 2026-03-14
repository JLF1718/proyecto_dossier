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

## Presentacion (modo ejecutivo)

- Refresco automatico cada 10 horas.
- Boton `Actualizar ahora` para refresco manual en vivo.
- Poster principal BAYSA con scroll optimizado.

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
- GET /api/tablas-posters
- GET /api/baysa-form-meta
- POST /api/baysa-block-status
- GET /api/baysa-status-history

## Acceso protegido (Fase 3)

Puedes proteger la API con una clave compartida:

```bash
$env:DOSSIER_WEB_ACCESS_KEY="tu_clave_segura"
python cli.py run-web
```

Si la clave esta activa:

- El frontend pedira autenticacion.
- La clave se envia por header (`x-access-key`), no se requiere exponerla en URL.
- Opcionalmente puedes abrir con `?k=tu_clave` y el frontend la guardara en sesion.

## Notas

- El frontend refresca automaticamente cada 10 horas y permite refresco manual.
- Si detienes la app local o cierras el tunel, el enlace publico deja de funcionar.
- Esta fase no modifica tus flujos de generacion ni Streamlit.

# QA Platform — Guia de uso

## 1. Primera vez (instalar)

Solo la primera vez que clones o tengas el proyecto limpio:

```bash
cd /root/workspace/projects/proyecto_dossier
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
make db-init
```

---

## 2. Arrancar el sistema

### Opcion A — Todo junto (backend + dashboard)

```bash
cd /root/workspace/projects/proyecto_dossier
source .venv/bin/activate
make dev
```

### Opcion B — Solo el dashboard

```bash
cd /root/workspace/projects/proyecto_dossier
source .venv/bin/activate
make dash
```

### Opcion C — Solo el backend API

```bash
cd /root/workspace/projects/proyecto_dossier
source .venv/bin/activate
make api
```

Una vez arrancado, abre en el navegador:

- **Dashboard** → http://localhost:8050
- **Backend API** → http://localhost:8000/api/docs

---

## 3. Editar datos (flujo seguro)

**Nunca edites el CSV directamente.** Usa el flujo de parche:

```bash
source .venv/bin/activate
make edit        # abre el editor interactivo
make validate    # verifica que el CSV este bien
make apply       # aplica los cambios (hace backup automatico)
make validate    # confirma que todo quedo bien
```

---

## 4. Operacion diaria (cierre de semana)

```bash
source .venv/bin/activate
make snapshot          # guarda snapshot semanal
make audit-kpis        # revisa KPIs y pesos
make inspect-management  # payload ejecutivo
make smoke             # prueba rapida de salud del sistema
```

---

## 5. Pruebas

```bash
source .venv/bin/activate
pytest -q
```

---

## 6. Parar el sistema

```bash
make qa-stop
```

O simplemente presiona `Ctrl+C` en la terminal donde esta corriendo.

---

## Reglas importantes

- **NO** edites `data/processed/baysa_dossiers_clean.csv` a mano — usa `make edit` / `make apply`.
- `make apply` crea un backup automatico en `data/processed/backups/`.
- Ejecuta todos los comandos desde la raiz del proyecto (donde esta el `Makefile`).

---

## Referencias

- Arquitectura: `docs/ARQUITECTURA_V2.md`
- Deploy en servidor Ubuntu: `docs/DEPLOY_UBUNTU.md`
- Guia de usuario: `docs/GUIA_USUARIO.md`

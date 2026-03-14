"""
Utilidades de respaldo automático para prevenir pérdida de datos.
Módulo de seguridad crítico para operaciones con archivos CSV.
"""

import shutil
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def crear_backup_automatico(archivo: Path, mantener_ultimos: int = 10) -> Path:
    """
    Crea backup automático de un archivo con timestamp.
    
    Args:
        archivo: Ruta del archivo a respaldar
        mantener_ultimos: Número de backups a mantener (default: 10)
    
    Returns:
        Path del archivo de backup creado
        
    Raises:
        FileNotFoundError: Si el archivo no existe
        IOError: Si falla la copia
    """
    if not archivo.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {archivo}")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{archivo.stem}_backup_{timestamp}{archivo.suffix}"
    backup_path = archivo.parent / backup_name
    
    try:
        shutil.copy2(archivo, backup_path)
        logger.info(f"✅ Backup creado: {backup_path.name}")
        logger.info(f"   Tamaño: {backup_path.stat().st_size:,} bytes")
        
        # Limpiar backups antiguos DESPUÉS de crear el nuevo
        # Esto asegura que el nuevo backup se cuenta en mantener_ultimos
        import time
        time.sleep(0.01)  # Pequeña pausa para asegurar timestamps diferentes
        limpiar_backups_antiguos(archivo, mantener_ultimos)
        
        return backup_path
    except Exception as e:
        logger.error(f"❌ Error al crear backup: {e}")
        raise IOError(f"No se pudo crear backup de {archivo.name}: {e}")


def limpiar_backups_antiguos(archivo_original: Path, mantener: int = 10):
    """
    Elimina backups antiguos manteniendo solo los N más recientes.
    
    Args:
        archivo_original: Archivo original del cual buscar backups
        mantener: Número de backups a mantener
    """
    patron = f"{archivo_original.stem}_backup_*{archivo_original.suffix}"
    backups = sorted(
        archivo_original.parent.glob(patron),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    
    # Eliminar backups excedentes (más antiguos)
    for backup_antiguo in backups[mantener:]:
        try:
            backup_antiguo.unlink()
            logger.info(f"🗑️  Backup antiguo eliminado: {backup_antiguo.name}")
        except Exception as e:
            logger.warning(f"⚠️  No se pudo eliminar backup antiguo {backup_antiguo.name}: {e}")


def verificar_integridad_backup(original: Path, backup: Path) -> bool:
    """
    Verifica que el backup sea válido comparando tamaños.
    
    Args:
        original: Ruta del archivo original
        backup: Ruta del archivo de backup
    
    Returns:
        True si el backup es válido, False en caso contrario
    """
    if not backup.exists():
        logger.error(f"❌ Backup no existe: {backup}")
        return False
    
    tam_original = original.stat().st_size
    tam_backup = backup.stat().st_size
    
    if tam_original != tam_backup:
        logger.warning(f"⚠️  Tamaño diferente: original={tam_original:,} backup={tam_backup:,}")
        return False
    
    logger.info(f"✅ Backup verificado: {backup.name} ({tam_backup:,} bytes)")
    return True


def restaurar_desde_backup(backup: Path, destino: Path) -> bool:
    """
    Restaura un archivo desde un backup.
    
    Args:
        backup: Ruta del archivo de backup
        destino: Ruta donde restaurar el archivo
    
    Returns:
        True si la restauración fue exitosa
    """
    if not backup.exists():
        logger.error(f"❌ Backup no encontrado: {backup}")
        return False
    
    try:
        # Crear backup del destino actual si existe
        if destino.exists():
            backup_previo = crear_backup_automatico(destino, mantener_ultimos=5)
            logger.info(f"📦 Backup del archivo actual creado: {backup_previo.name}")
        
        shutil.copy2(backup, destino)
        logger.info(f"✅ Archivo restaurado desde: {backup.name}")
        logger.info(f"   Destino: {destino}")
        return True
    except Exception as e:
        logger.error(f"❌ Error al restaurar: {e}")
        return False


def listar_backups_disponibles(archivo: Path) -> list[Path]:
    """
    Lista todos los backups disponibles para un archivo.
    
    Args:
        archivo: Archivo original del cual buscar backups
    
    Returns:
        Lista de rutas de backups ordenados por fecha (más reciente primero)
    """
    patron = f"{archivo.stem}_backup_*{archivo.suffix}"
    backups = sorted(
        archivo.parent.glob(patron),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    return backups


def crear_backup_directorio(directorio: Path, sufijo: str = "") -> Path:
    """
    Crea backup completo de un directorio.
    
    Args:
        directorio: Directorio a respaldar
        sufijo: Sufijo opcional para el nombre del backup
    
    Returns:
        Path del directorio de backup creado
    """
    if not directorio.exists():
        raise FileNotFoundError(f"Directorio no encontrado: {directorio}")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_backup = f"{directorio.name}_backup_{timestamp}{sufijo}"
    backup_path = directorio.parent / nombre_backup
    
    try:
        shutil.copytree(directorio, backup_path)
        logger.info(f"✅ Backup de directorio creado: {backup_path.name}")
        return backup_path
    except Exception as e:
        logger.error(f"❌ Error al crear backup de directorio: {e}")
        raise


# Uso de ejemplo en otros scripts:
if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Ejemplo de uso
    archivo_ejemplo = Path("data/contratistas/BAYSA/ctrl_dosieres_BAYSA_normalizado.csv")
    
    if archivo_ejemplo.exists():
        backup = crear_backup_automatico(archivo_ejemplo)
        print(f"\nBackup creado exitosamente: {backup}")
        
        # Listar backups disponibles
        print("\nBackups disponibles:")
        for i, bp in enumerate(listar_backups_disponibles(archivo_ejemplo), 1):
            print(f"  {i}. {bp.name} ({bp.stat().st_size:,} bytes)")
    else:
        print(f"Archivo no encontrado: {archivo_ejemplo}")

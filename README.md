# VisionStock

Sistema de inventario con visión artificial (Django). Cuenta fotos de estanterías con un modelo
YOLO11 entrenado en SKU-110K, reconoce cada producto con CLIP y lo compara con el stock registrado.

## Módulos

| App | Qué hace |
| --- | --- |
| `accounts` | Login, registro, usuarios, **grupos** y **permisos** (solo administradores) |
| `catalog` | Productos, categorías e imágenes de referencia (CRUD con permisos) |
| `inventory` | Movimientos de stock (entrada / salida / ajuste) y **alertas** automáticas |
| `vision` | Análisis de fotos con YOLO + CLIP, historial y ajuste del inventario |
| `dashboard` | Pantalla de inicio con el resumen |

## Puesta en marcha (Windows)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install torch==2.14.1 torchvision==0.29.1 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Abre http://127.0.0.1:8000/

**Administrador por defecto** (se crea al migrar): usuario `admin`, contraseña `admin2026`.
Los usuarios que se registran quedan en el grupo `Consulta` (solo lectura). Desde *Grupos* y *Permisos*
el administrador cambia qué puede hacer cada grupo.

## Cómo usar el análisis

1. Crea los productos y súbele 3–5 fotos de referencia a cada uno (ficha del producto → *Gestionar*).
2. En *Analizar* sube la foto de una estantería.
3. Revisa el conteo por producto; las diferencias con el stock generan alertas y puedes
   aplicar el ajuste al inventario con un clic.

### Cómo reconoce los productos

1. **OWLv2** (`google/owlv2-base-patch16-ensemble`) propone cajas de cualquier objeto y **YOLO11 SKU-110K**
   (`sku110k-yolo11-s640.pt`) aporta las cajas en estanterías densas.
2. **CLIP** (`clip-ViT-B-32`) compara el recorte de cada caja con las fotos de referencia de cada producto.
3. Solo se acepta una coincidencia clara (similitud ≥ 0.80 y ventaja sobre el segundo producto); de las cajas
   que se pisan gana la de mayor similitud, así cada objeto se cuenta una vez.

Los modelos de Hugging Face (~1 GB) se descargan solos la primera vez. Cada análisis tarda ~8–25 s en CPU.
Sube 3–5 fotos por producto (distintos ángulos). Si cambias el modelo o los umbrales, recalcula las
referencias con `python manage.py recalcular_embeddings`.

## Pruebas

```powershell
python manage.py test
```

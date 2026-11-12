from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from inventory.models import Alert, StockMovement
from vision.models import Inspection

from .models import Category, Product, ReferenceImage


# ---------- Inicio ----------

@login_required
def home(request):
  productos = Product.objects.all()
  bajos = productos.filter(stock__lte=F('min_stock')).order_by('stock')[:6]
  return render(request, 'catalogo/home.html', {
      'total_productos': productos.count(),
      'total_categorias': Category.objects.count(),
      'unidades': sum(productos.values_list('stock', flat=True)),
      'alertas_abiertas': Alert.objects.filter(is_resolved=False).count(),
      'bajos': bajos,
      'movimientos': StockMovement.objects.select_related('product')[:6],
      'analisis': Inspection.objects.count(),
      'ultimos_analisis': Inspection.objects.all()[:4],
  })


# ---------- Productos ----------

@login_required
@permission_required('catalog.view_product', raise_exception=True)
def product_list(request):
  products = Product.objects.select_related('category')
  q = request.GET.get('q', '').strip()
  categoria = request.GET.get('categoria', '')
  if q:
    products = products.filter(Q(name__icontains=q) | Q(description__icontains=q))
  if categoria.isdigit():
    products = products.filter(category_id=categoria)
  return render(request, 'catalogo/product_list.html', {
      'products': products,
      'categories': Category.objects.all(),
      'q': q,
      'categoria': categoria,
  })


def leer_producto(request):
  # Lee los datos del formulario HTML y los valida; devuelve (valores, error)
  valores = {
      'name': request.POST.get('name', '').strip(),
      'category': request.POST.get('category', ''),
      'price': request.POST.get('price', '').strip(),
      'stock': request.POST.get('stock', '0').strip(),
      'min_stock': request.POST.get('min_stock', '0').strip(),
      'description': request.POST.get('description', '').strip(),
  }
  if not valores['name']:
    return valores, 'El nombre es obligatorio.'
  try:
    if Decimal(valores['price']) < 0:
      return valores, 'El precio no puede ser negativo.'
  except InvalidOperation:
    return valores, 'El precio no es un número válido.'
  if not valores['stock'].isdigit() or not valores['min_stock'].isdigit():
    return valores, 'El stock y el stock mínimo deben ser números enteros.'
  return valores, None


def guardar_producto(product, valores):
  # Copia los valores validados al producto y lo guarda
  product.name = valores['name']
  product.category = Category.objects.filter(pk=valores['category']).first() if valores['category'].isdigit() else None
  product.price = Decimal(valores['price'])
  product.stock = int(valores['stock'])
  product.min_stock = int(valores['min_stock'])
  product.description = valores['description']
  product.save()


@login_required
@permission_required('catalog.add_product', raise_exception=True)
def product_create(request):
  valores = {'stock': 0, 'min_stock': 5}
  if request.method == 'POST':
    valores, error = leer_producto(request)
    if error:
      messages.error(request, error)
    else:
      product = Product()
      guardar_producto(product, valores)
      messages.success(request, f'Producto «{product.name}» creado.')
      return redirect('product_detail', pk=product.pk)
  return render(request, 'catalogo/product_form.html', {
      'valores': valores, 'categories': Category.objects.all(), 'titulo': 'Nuevo producto'})


@login_required
@permission_required('catalog.view_product', raise_exception=True)
def product_detail(request, pk):
  product = get_object_or_404(Product.objects.select_related('category'), pk=pk)
  return render(request, 'catalogo/product_detail.html', {
      'product': product,
      'references': product.references.all(),
      'movements': product.movements.select_related('created_by')[:8],
  })


@login_required
@permission_required('catalog.change_product', raise_exception=True)
def product_edit(request, pk):
  product = get_object_or_404(Product, pk=pk)
  valores = {
      'name': product.name, 'category': str(product.category_id or ''), 'price': str(product.price),
      'stock': product.stock, 'min_stock': product.min_stock, 'description': product.description or ''}
  if request.method == 'POST':
    valores, error = leer_producto(request)
    if error:
      messages.error(request, error)
    else:
      guardar_producto(product, valores)
      messages.success(request, 'Producto actualizado.')
      return redirect('product_detail', pk=product.pk)
  return render(request, 'catalogo/product_form.html', {
      'valores': valores, 'categories': Category.objects.all(),
      'titulo': f'Editar {product.name}', 'product': product})


@login_required
@permission_required('catalog.delete_product', raise_exception=True)
@require_POST
def product_delete(request, pk):
  product = get_object_or_404(Product, pk=pk)
  nombre = product.name
  product.delete()
  messages.success(request, f'Producto «{nombre}» eliminado.')
  return redirect('product_list')


# ---------- Categorías ----------

@login_required
@permission_required('catalog.view_category', raise_exception=True)
def category_list(request):
  return render(request, 'catalogo/category_list.html', {
      'categories': Category.objects.prefetch_related('products')})


@login_required
@permission_required('catalog.add_category', raise_exception=True)
def category_create(request):
  valores = {}
  siguiente = request.GET.get('next', '')
  if request.method == 'POST':
    valores = {'name': request.POST.get('name', '').strip(), 'description': request.POST.get('description', '').strip()}
    if not valores['name']:
      messages.error(request, 'El nombre es obligatorio.')
    elif Category.objects.filter(name=valores['name']).exists():
      messages.error(request, 'Ya existe una categoría con ese nombre.')
    else:
      Category.objects.create(name=valores['name'], description=valores['description'])
      messages.success(request, 'Categoría creada.')
      if siguiente in ('product_create',):  # vuelve al formulario de producto
        return redirect(siguiente)
      return redirect('category_list')
  return render(request, 'catalogo/category_form.html', {'valores': valores, 'titulo': 'Nueva categoría'})


@login_required
@permission_required('catalog.change_category', raise_exception=True)
def category_edit(request, pk):
  category = get_object_or_404(Category, pk=pk)
  valores = {'name': category.name, 'description': category.description or ''}
  if request.method == 'POST':
    valores = {'name': request.POST.get('name', '').strip(), 'description': request.POST.get('description', '').strip()}
    if not valores['name']:
      messages.error(request, 'El nombre es obligatorio.')
    elif Category.objects.filter(name=valores['name']).exclude(pk=pk).exists():
      messages.error(request, 'Ya existe una categoría con ese nombre.')
    else:
      category.name = valores['name']
      category.description = valores['description']
      category.save()
      messages.success(request, 'Categoría actualizada.')
      return redirect('category_list')
  return render(request, 'catalogo/category_form.html', {
      'valores': valores, 'titulo': f'Editar {category.name}'})


@login_required
@permission_required('catalog.delete_category', raise_exception=True)
@require_POST
def category_delete(request, pk):
  category = get_object_or_404(Category, pk=pk)
  nombre = category.name
  category.delete()  # los productos quedan "sin categoría" (SET_NULL)
  messages.success(request, f'Categoría «{nombre}» eliminada.')
  return redirect('category_list')


# ---------- Imágenes de referencia ----------

@login_required
@permission_required('catalog.add_referenceimage', raise_exception=True)
def upload_references(request, pk):
  from PIL import Image, ImageOps
  from visionstock_project.ia.buscador import MLUnavailable, vectores_referencia

  product = get_object_or_404(Product, pk=pk)
  if request.method == 'POST':
    archivos = request.FILES.getlist('image')
    if not archivos:
      messages.error(request, 'Selecciona al menos una imagen.')
    else:
      guardadas, sin_embedding = 0, 0
      for archivo in archivos:
        ref = ReferenceImage(product=product, image=archivo)
        ref.save()
        try:
          with Image.open(ref.image.path) as img:
            ref.embedding = vectores_referencia(ImageOps.exif_transpose(img).convert('RGB'))
          ref.save(update_fields=['embedding'])
        except MLUnavailable:
          sin_embedding += 1
        except Exception:
          ref.delete()
          messages.error(request, f'«{archivo.name}» no es una imagen válida.')
          continue
        guardadas += 1
      if guardadas:
        messages.success(request, f'{guardadas} imagen(es) de referencia guardada(s).')
      if sin_embedding:
        messages.warning(
            request, 'Los modelos de reconocimiento no están disponibles: las imágenes se guardaron '
            'pero aún no sirven para reconocer productos.')
      return redirect('upload_references', pk=product.pk)
  return render(request, 'catalogo/upload_references.html', {
      'product': product, 'references': product.references.all()})


@login_required
@permission_required('catalog.delete_referenceimage', raise_exception=True)
@require_POST
def reference_delete(request, pk):
  ref = get_object_or_404(ReferenceImage, pk=pk)
  product_id = ref.product_id
  ref.image.delete(save=False)
  ref.delete()
  messages.success(request, 'Imagen de referencia eliminada.')
  return redirect('upload_references', pk=product_id)

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import CategoryForm, ProductForm, ReferenceImageForm
from .models import Category, Product, ReferenceImage


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


@login_required
@permission_required('catalog.add_product', raise_exception=True)
def product_create(request):
  form = ProductForm(request.POST or None)
  if request.method == 'POST' and form.is_valid():
    product = form.save()
    messages.success(request, f'Producto «{product.name}» creado.')
    return redirect('product_detail', pk=product.pk)
  return render(request, 'catalogo/product_form.html', {'form': form, 'titulo': 'Nuevo producto'})


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
  form = ProductForm(request.POST or None, instance=product)
  if request.method == 'POST' and form.is_valid():
    form.save()
    messages.success(request, 'Producto actualizado.')
    return redirect('product_detail', pk=product.pk)
  return render(request, 'catalogo/product_form.html', {
      'form': form, 'titulo': f'Editar {product.name}', 'product': product})


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
  form = CategoryForm(request.POST or None)
  siguiente = request.GET.get('next', '')
  if request.method == 'POST' and form.is_valid():
    form.save()
    messages.success(request, 'Categoría creada.')
    if siguiente in ('product_create',):  # vuelve al formulario de producto
      return redirect(siguiente)
    return redirect('category_list')
  return render(request, 'catalogo/category_form.html', {'form': form, 'titulo': 'Nueva categoría'})


@login_required
@permission_required('catalog.change_category', raise_exception=True)
def category_edit(request, pk):
  category = get_object_or_404(Category, pk=pk)
  form = CategoryForm(request.POST or None, instance=category)
  if request.method == 'POST' and form.is_valid():
    form.save()
    messages.success(request, 'Categoría actualizada.')
    return redirect('category_list')
  return render(request, 'catalogo/category_form.html', {
      'form': form, 'titulo': f'Editar {category.name}'})


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
  from PIL import Image
  from vision.ml import MLUnavailable
  from vision.services import reference_vectors

  product = get_object_or_404(Product, pk=pk)
  form = ReferenceImageForm(request.POST or None, request.FILES or None)
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
            ref.embedding = reference_vectors(img)
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
      'product': product, 'form': form, 'references': product.references.all()})


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

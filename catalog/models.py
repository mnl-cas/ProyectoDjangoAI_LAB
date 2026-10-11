from django.db import models


class Category(models.Model):
  name = models.CharField(
      max_length=100, unique=True, verbose_name='Nombre de la Categoría'
  )
  description = models.TextField(
      blank=True, null=True, verbose_name='Descripción'
  )

  class Meta:
    verbose_name = 'Categoría'
    verbose_name_plural = 'Categorías'
    ordering = ['name']

  def __str__(self):
    return self.name


class Product(models.Model):
  name = models.CharField(max_length=150, verbose_name='Nombre del Producto')
  category = models.ForeignKey(
      Category,
      on_delete=models.SET_NULL,
      null=True,
      blank=True,
      related_name='products',
      verbose_name='Categoría',
  )
  price = models.DecimalField(
      max_digits=10, decimal_places=2, verbose_name='Precio'
  )
  stock = models.PositiveIntegerField(
      default=0, verbose_name='Stock Disponible'
  )
  min_stock = models.PositiveIntegerField(
      default=5, verbose_name='Stock Mínimo'
  )
  description = models.TextField(
      blank=True, null=True, verbose_name='Descripción del Producto'
  )
  created_at = models.DateTimeField(
      auto_now_add=True, verbose_name='Fecha de Creación'
  )

  class Meta:
    verbose_name = 'Producto'
    verbose_name_plural = 'Productos'
    ordering = ['-created_at']

  def __str__(self):
    return f'{self.name} (${self.price})'

  @property
  def is_low_stock(self):
    return self.stock <= self.min_stock


class ReferenceImage(models.Model):
  """Foto de referencia de un producto; el embedding CLIP sirve para reconocerlo."""

  product = models.ForeignKey(
      Product, on_delete=models.CASCADE, related_name='references',
      verbose_name='Producto',
  )
  image = models.ImageField(upload_to='references/', verbose_name='Imagen')
  embedding = models.JSONField(blank=True, null=True)
  created_at = models.DateTimeField(auto_now_add=True)

  class Meta:
    verbose_name = 'Imagen de referencia'
    verbose_name_plural = 'Imágenes de referencia'
    ordering = ['-created_at']

  def __str__(self):
    return f'Referencia de {self.product.name} #{self.pk}'

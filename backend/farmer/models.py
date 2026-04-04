from django.db import models
from django.utils.translation import gettext as _
from django.contrib.auth import get_user_model

from wagtail.admin.panels import FieldPanel, MultiFieldPanel

# Create your models here.

class DocumentType(models.TextChoices):
    CC = 'CC', _('Cédula de Ciudadanía')
    CE = 'CE', _('Cédula de Extranjería')
    PASSPORT = 'PASSPORT', _('Pasaporte')


class GenderType(models.TextChoices):
    MALE = "M", _("Masculino")
    FEMALE = "F", _("Femenino")


class Farmer(models.Model):

    user = models.OneToOneField(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name='farmer',
        help_text=_('Usuario asociado al agricultor'),
        verbose_name=_('Usuario')
    )
    organization = models.ForeignKey(
        'Organization',
        on_delete=models.CASCADE,
        related_name='farmers',
        null=True,
        blank=True,
        help_text=_('Opcional: Organización a la que pertenece el agricultor'),
        verbose_name=_('Organización')
    )
    avatar = models.ImageField(
        upload_to='farmer/avatars/',
        null=True,
        blank=True,
        help_text=_('Imagen de perfil del agricultor'),
        verbose_name=_('Avatar')
    )

    first_name = models.CharField(
        max_length=30, 
        null=True, 
        blank=True, 
        help_text=_('Nombre del agricultor'),
        verbose_name=_('Nombre')
    )
    last_name = models.CharField(
        max_length=30, 
        null=True, 
        blank=True, 
        help_text=_('Apellido del agricultor'),
        verbose_name=_('Apellido')
    )
    document_type = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=DocumentType.choices,
        help_text=_('Tipo de documento de identificación del agricultor'),
        verbose_name=_('Tipo de documento')
    )
    gender = models.CharField(
        max_length=1,
        null=True,
        blank=True,
        choices=GenderType.choices,
        help_text=_('Género del agricultor'),
        verbose_name=_('Género')
    )
    document_number = models.CharField(
        max_length=20, 
        null=True, 
        blank=True, 
        help_text=_('Número de documento de identificación del agricultor'),
        verbose_name=_('Número de documento')
    )
    phone_number = models.CharField(
        max_length=20, 
        null=True, 
        blank=True, 
        help_text=_('Número de teléfono del agricultor'),
        verbose_name=_('Número de teléfono')
    )
    city = models.CharField(
        max_length=50, 
        null=True, 
        blank=True, 
        help_text=_('Ciudad de residencia del agricultor'),
        verbose_name=_('Ciudad')
    )
    department = models.CharField(
        max_length=50, 
        null=True, 
        blank=True, 
        help_text=_('Departamento de residencia del agricultor'),
        verbose_name=_('Departamento')
    )
    address = models.CharField(
        max_length=100, 
        null=True, 
        blank=True, 
        help_text=_('Dirección de residencia del agricultor'),
        verbose_name=_('Dirección')
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_('Indica si el agricultor está activo'),
        verbose_name=_('Activo')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_('Fecha de creación del agricultor')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text=_('Fecha de actualización del agricultor')
    )

    panels = [
        MultiFieldPanel([
            FieldPanel('user'),
            FieldPanel('first_name'),
            FieldPanel('last_name'),
            FieldPanel('organization'),
            FieldPanel('avatar'),
        ], heading=_('Información personal')),
        MultiFieldPanel([
            FieldPanel('document_type'),
            FieldPanel('document_number'),
            FieldPanel('gender'),
        ], heading=_('Información de identificación')),
        MultiFieldPanel([
            FieldPanel('phone_number'),
            FieldPanel('city'),
            FieldPanel('department'),
            FieldPanel('address'),
        ], heading=_('Información de contacto')),
        FieldPanel('is_active'),
        MultiFieldPanel([
            FieldPanel('created_at', read_only=True),
            FieldPanel('updated_at', read_only=True),
        ], heading=_('Metadata')),
    ]

    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Organization(models.Model):
    name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text=_('Nombre de la organización')
    )
    nit = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text=_('Número de identificación tributaria de la organización')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_('Fecha de creación de la organización')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text=_('Fecha de actualización de la organización')
    )
    panels = [
        MultiFieldPanel([
            FieldPanel('name'),
            FieldPanel('nit'),
        ], heading=_('Información de la organización')),
        MultiFieldPanel([
            FieldPanel('created_at', read_only=True),
            FieldPanel('updated_at', read_only=True),
        ], heading=_('Metadata')),
    ]
    
    def __str__(self):
        return self.name
    
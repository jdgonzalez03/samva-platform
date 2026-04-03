from django.utils.translation import gettext_lazy as _

from django.db import models
from wagtail.contrib.settings.models import BaseSiteSetting, register_setting

from wagtail.admin.panels import FieldPanel

# Create your models here.
@register_setting
class GeneralSiteSettings(BaseSiteSetting):
    contact_email = models.EmailField(
        blank=True,
        null=True,
        help_text=_("Email de contacto para la página"),
        verbose_name=_("Email de contacto")
    )
    contact_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text=_("Teléfono de contacto para la página"),
        verbose_name=_("Teléfono de contacto")
    )
    location = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text=_("Ubicación de la empresa"),
        verbose_name=_("Ubicación")
    )
    
    panels = [
        FieldPanel('contact_email'),
        FieldPanel('contact_phone'),
        FieldPanel('location'),
    ]


@register_setting
class SocialMediaSettings(BaseSiteSetting):
    facebook = models.URLField(
        blank=True,
        null=True,
        help_text=_("URL de Facebook"),
        verbose_name=_("Facebook")
    )
    twitter = models.URLField(
        blank=True,
        null=True,
        help_text=_("URL de Twitter"),
        verbose_name=_("Twitter")
    )
    instagram = models.URLField(
        blank=True,
        null=True,
        help_text=_("URL de Instagram"),
        verbose_name=_("Instagram")
    )
    
    panels = [
        FieldPanel('facebook'),
        FieldPanel('twitter'),
        FieldPanel('instagram'),
    ]
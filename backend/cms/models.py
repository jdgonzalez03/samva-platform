from django.utils.translation import gettext_lazy as _

from wagtail.models import Page
from wagtail.fields import StreamField, RichTextField
from wagtail.admin.panels import FieldPanel

from cms.blocks import LandingStreamBlocks


# Create your models here.
class LandingPage(Page):
    body = StreamField(
        LandingStreamBlocks(),
        null=True,
        blank=True,
        use_json_field=True,
        help_text=_("Contenido de la página principal"),
    )

    content_panels = Page.content_panels + [
        FieldPanel("body"),
    ]

    max_count = 1

    class Meta:
        verbose_name = _("Página de inicio")
        verbose_name_plural = _("Páginas de inicio")


class GeneralPage(Page):
    body = RichTextField()
    
    content_panels = Page.content_panels + [
        FieldPanel("body"),
    ]
    
    class Meta:
        verbose_name = _("Página general")
        verbose_name_plural = _("Páginas generales")

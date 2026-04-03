from django.utils.translation import gettext_lazy as _

from wagtail.blocks import StreamBlock, StructBlock, CharBlock, TextBlock


class HeroBlock(StructBlock):
    badge = CharBlock(
        required=True,
        label=_("Anuncio"),
        help_text=_("Texto del anuncio"),
        default="Integración con Estaciones Meteorológicas",
    )
    title = CharBlock(
        required=True,
        label=_("Título"),
        help_text=_("Título del hero"),
        default="Agricultura de Precisión",
    )
    highlight_text = CharBlock(
        required=True,
        label=_("Titulo Resaltado"),
        help_text=_("Titulo resaltado del hero"),
        default="Inteligente y Sostenible",
    )
    description = TextBlock(
        required=True,
        label=_("Descripción"),
        help_text=_("Descripción del hero"),
        default="Gestiona tus datos meteorológicos con facilidad",
    )
    cta_text = CharBlock(
        required=True,
        label=_("Texto CTA"),
        help_text=_("Texto del CTA"),
        default="Comenzar ahora",
    )
    cta_url = CharBlock(
        required=True,
        label=_("URL CTA"),
        help_text=_("URL del CTA"),
        default="#",
    )

    class Meta:
        icon = "image"
        label = _("Hero")
    






class LandingStreamBlocks(StreamBlock):
    hero = HeroBlock()
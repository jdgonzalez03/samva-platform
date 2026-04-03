from django.utils.translation import gettext_lazy as _

from wagtail.blocks import StreamBlock, StructBlock, CharBlock, TextBlock, ChoiceBlock

from cms.utils import ICON_CHOICES, BACKGROUND_CHOICES

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
    cta_icon = ChoiceBlock(
        required=True,
        choices=ICON_CHOICES,
        default=ICON_CHOICES[0][0],
        label=_("Icono CTA"),
        help_text=_("Icono del CTA"),
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
    

class CardBlock(StructBlock):
    title = CharBlock(
        required=True,
        label=_("Título"),
        help_text=_("Título de la tarjeta"),
        default="Tarjeta",
    )
    description = TextBlock(
        required=True,
        label=_("Descripción"),
        help_text=_("Descripción de la tarjeta"),
        default="Descripción de la tarjeta",
    )
    icon = ChoiceBlock(
        required=True,
        choices=ICON_CHOICES,
        default=ICON_CHOICES[0][0],
        label=_("Icono"),
        help_text=_("Icono de la tarjeta"),
    )

    class Meta:
        icon = "table"
        label = _("Tarjeta")


class VisionMisionSectionBlock(StructBlock):
    background = ChoiceBlock(
        required=True,
        choices=BACKGROUND_CHOICES,
        default=BACKGROUND_CHOICES[0][0],
        label=_("Fondo"),
        help_text=_("Fondo de la sección"),
    )
    vision = CardBlock()
    mision = CardBlock()

    class Meta:
        icon = "eye"
        label = _("Visión y Misión")
        


class LandingStreamBlocks(StreamBlock):
    hero = HeroBlock()
    vision_mision = VisionMisionSectionBlock()
from django.utils.translation import gettext_lazy as _

from wagtail.blocks import StreamBlock, StructBlock, CharBlock, TextBlock, ChoiceBlock, ListBlock

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
        icon = "success"
        label = _("Visión y Misión")



class HighlightBlock(StructBlock):
    title = CharBlock(
        required=True,
        label=_("Título"),
        help_text=_("Título del highlight"),
    )
    icon = ChoiceBlock(
        required=True,
        choices=ICON_CHOICES,
        default=ICON_CHOICES[0][0],
        label=_("Icono"),
        help_text=_("Icono del highlight"),
    )
    items = ListBlock(
        CharBlock(
            required=True,
            label=_("Item"),
            help_text=_("Item del highlight"),
            default="Item",
        ),
        required=True,
        label=_("Items"),
        help_text=_("Items del highlight"),
    )
    
    class Meta:
        icon = "doc-full"
        label = _("Highlight")


class SplitSectionBlock(StructBlock):
    background = ChoiceBlock(
        required=True,
        choices=BACKGROUND_CHOICES,
        default=BACKGROUND_CHOICES[0][0],
        label=_("Fondo"),
        help_text=_("Fondo de la sección"),
    )
    title = CharBlock(
        required=True,
        label=_("Título"),
        help_text=_("Título de la sección"),
        default="Sección dividida",
    )
    description = TextBlock(
        required=True,
        label=_("Descripción"),
        help_text=_("Descripción de la sección"),
    )
    highlight = HighlightBlock()

    
    class Meta:
        icon = "doc-full"
        label = _("Sección dividida con Highlight")


class HeadingTextBlock(StructBlock):
    title = CharBlock(
        required=True,
        label=_("Título"),
        help_text=_("Título de la sección"),
    )
    text = TextBlock(
        required=True,
        label=_("Texto"),
        help_text=_("Texto de la sección"),
    )
    
    class Meta:
        icon = "doc-full"
        label = _("Título con Texto")


class BenefitBlock(StructBlock):
    background = ChoiceBlock(
        required=True,
        choices=BACKGROUND_CHOICES,
        default=BACKGROUND_CHOICES[0][0],
        label=_("Fondo"),
        help_text=_("Fondo de la sección"),
    )
    heading = HeadingTextBlock()
    items = ListBlock(
        CardBlock()
    )
    
    class Meta:
        icon = "doc-full"
        label = _("Beneficios")


class LandingStreamBlocks(StreamBlock):
    hero = HeroBlock()
    vision_mision = VisionMisionSectionBlock()
    split_section = SplitSectionBlock()
    benefits = BenefitBlock()
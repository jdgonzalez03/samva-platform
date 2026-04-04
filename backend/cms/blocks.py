from django.utils.translation import gettext_lazy as _

from wagtail.blocks import StreamBlock, StructBlock, CharBlock, TextBlock, ChoiceBlock, ListBlock
from wagtail.images.blocks import ImageBlock

from cms.utils import ICON_CHOICES, BACKGROUND_CHOICES


class TitleBlock(StructBlock):
    title = CharBlock(
        required=True,
        label=_("Título"),
        help_text=_("Título"),
        default="Agricultura de Precisión",
    )
    highlight_text = CharBlock(
        required=True,
        label=_("Titulo Resaltado"),
        help_text=_("Titulo resaltado"),
        default="Inteligente y Sostenible",
    )

    def get_api_representation(self, value, context=None):
        return {
            "title": value["title"],
            "highlight_text": value["highlight_text"],
        }


class ButtonBlock(StructBlock):
    text = CharBlock(
        required=True,
        label=_("Texto"),
        help_text=_("Texto del botón"),
        default="Comenzar ahora",
    )
    icon = ChoiceBlock(
        required=True,
        choices=ICON_CHOICES,
        default=ICON_CHOICES[0][0],
        label=_("Icono"),
        help_text=_("Icono del botón"),
    )
    url = CharBlock(
        required=True,
        label=_("URL"),
        help_text=_("URL del CTA"),
        default="#",
    )

    def get_api_representation(self, value, context=None):
        return {
            "text": value["text"],
            "icon": value["icon"],
            "url": value["url"],
        }


class HeroBlock(StructBlock):
    badge = CharBlock(
        required=True,
        label=_("Anuncio"),
        help_text=_("Texto del anuncio"),
        default="Integración con Estaciones Meteorológicas",
    )
    title = TitleBlock(
        required=True,
        label=_("Título"),
        help_text=_("Título del hero"),
    )
    description = TextBlock(
        required=True,
        label=_("Descripción"),
        help_text=_("Descripción del hero"),
        default="Gestiona tus datos meteorológicos con facilidad",
    )
    cta_button = ButtonBlock(
        required=True,
        label=_("Botón CTA"),
        help_text=_("Botón CTA"),
    )

    class Meta:
        icon = "image"
        label = _("Hero")
    
    def get_api_representation(self, value, context=None):
        return {
            "badge": value["badge"],
            "title": value["title"],
            "description": value["description"],
            "cta_button": value["cta_button"],
        }


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
    
    def get_api_representation(self, value, context=None):
        return {
            "title": value["title"],
            "description": value["description"],
            "icon": value["icon"],
        }


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
    
    def get_api_representation(self, value, context=None):
        return {
            "background": value["background"],
            "vision": value["vision"],
            "mision": value["mision"],
        }


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
    
    def get_api_representation(self, value, context=None):
        return {
            "title": value["title"],
            "icon": value["icon"],
            "items": value["items"],
        }


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
    
    def get_api_representation(self, value, context=None):
        return {
            "title": value["title"],
            "text": value["text"],
        }


class TwoColumnsContentBlock(StructBlock):
    background = ChoiceBlock(
        required=True,
        choices=BACKGROUND_CHOICES,
        default=BACKGROUND_CHOICES[0][0],
        label=_("Fondo"),
        help_text=_("Fondo de la sección"),
    )
    left_column = HeadingTextBlock()
    right_column = HeadingTextBlock()
    
    class Meta:
        icon = "doc-full"
        label = _("Contenido en Dos Columnas")
    
    def get_api_representation(self, value, context=None):
        return {
            "background": value["background"],
            "left_column": value["left_column"],
            "right_column": value["right_column"],
        }


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
    
    def get_api_representation(self, value, context=None):
        return {
            "background": value["background"],
            "heading": value["heading"],
            "items": value["items"],
        }


class MemberBlock(StructBlock):
    name = CharBlock(
        required=True,
        label=_("Nombre"),
        help_text=_("Nombre del miembro, ej: Ing.Juan Pérez"),
    )
    role = CharBlock(
        required=True,
        label=_("Rol"),
        help_text=_("Rol del miembro, ej: Especialista IoT o Ingenieria Electrónica"),
    )
    image = ImageBlock(
        required=True,
        label=_("Imagen"),
        help_text=_("Imagen del miembro"),
    )
    description = TextBlock(
        required=True,
        label=_("Descripción"),
        help_text=_("Descripción del miembro"),
    )
    
    class Meta:
        icon = "doc-full"
        label = _("Miembro")

    def get_api_representation(self, value, context=None):
        return {
            "name": value["name"],
            "role": value["role"],
            "image": value["image"],
            "description": value["description"],
        }


class TeamBlock(StructBlock):
    background = ChoiceBlock(
        required=True,
        choices=BACKGROUND_CHOICES,
        default=BACKGROUND_CHOICES[0][0],
        label=_("Fondo"),
        help_text=_("Fondo de la sección"),
    )
    heading = HeadingTextBlock()
    members = ListBlock(
        MemberBlock()
    )
    
    class Meta:
        icon = "doc-full"
        label = _("Equipo")

    def get_api_representation(self, value, context=None):
        return {
            "background": value["background"],
            "heading": value["heading"],
            "members": value["members"],
        }

class ListItemsBlock(StructBlock):
    list_icon = ChoiceBlock(
        required=True,
        choices=ICON_CHOICES,
        default=ICON_CHOICES[0][0],
        label=_("Icono"),
        help_text=_("Icono de la lista"),
    )
    items = ListBlock(
        StructBlock([
            ("text", CharBlock()),
        ])
    )


class BadgeBlock(StructBlock):
    text = CharBlock(
        required=True,
        label=_("Texto"),
        help_text=_("Texto del badge"),
    )
    status = CharBlock(
        required=True,
        label=_("Estado"),
        help_text=_("Estado del badge"),
    )
    icon = ChoiceBlock(
        required=True,
        choices=ICON_CHOICES,
        default=ICON_CHOICES[0][0],
        label=_("Icono"),
        help_text=_("Icono del badge"),
    )
    
    def get_api_representation(self, value, context=None):
        return {
            "text": value["text"],
            "status": value["status"],
            "icon": value["icon"],
        }


class FeatureHighlightBlock(StructBlock):
    background = ChoiceBlock(
        required=True,
        choices=BACKGROUND_CHOICES,
        default=BACKGROUND_CHOICES[0][0],
        label=_("Fondo"),
        help_text=_("Fondo de la sección"),
    )
    imagen = ImageBlock(
        required=True,
        label=_("Imagen"),
        help_text=_("Imagen de la sección"),
    )
    title = TitleBlock()
    description = TextBlock(
        required=True,
        label=_("Descripción"),
        help_text=_("Descripción de la sección"),
    )
    items = ListItemsBlock()
    badge = BadgeBlock()
    
    class Meta:
        icon = "doc-full"
        label = _("Feature Highlight")
    
    def get_api_representation(self, value, context=None):
        return {
            "background": value["background"],
            "imagen": value["imagen"],
            "title": value["title"],
            "description": value["description"],
            "items": value["items"],
            "badge": value["badge"],
        }


class CTASectionBlock(StructBlock):
    background = ChoiceBlock(
        required=True,
        choices=BACKGROUND_CHOICES,
        default=BACKGROUND_CHOICES[0][0],
        label=_("Fondo"),
        help_text=_("Fondo de la sección"),
    )
    heading = HeadingTextBlock()
    cta_button = ButtonBlock()


    class Meta:
        icon = "doc-full"
        label = _("CTA Section")
    
    def get_api_representation(self, value, context=None):
        return {
            "background": value["background"],
            "heading": value["heading"],
            "cta_button": value["cta_button"],
        }


class LandingStreamBlocks(StreamBlock):
    hero = HeroBlock()
    vision_mision = VisionMisionSectionBlock()
    two_columns_content = TwoColumnsContentBlock()
    benefits = BenefitBlock()
    team = TeamBlock()
    feature_highlight = FeatureHighlightBlock()
    cta_section = CTASectionBlock()
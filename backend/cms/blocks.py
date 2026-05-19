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
            "items": list(value["items"]),
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
        card_block = CardBlock()
        return {
            "background": value["background"],
            "heading": self.child_blocks["heading"].get_api_representation(
                value["heading"], context
            ),
            "items": [
                card_block.get_api_representation(item, context)
                for item in value["items"]
            ],
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
        image_data = None
        if value["image"]:
            image_data = {
                "id": value["image"].id,
                "title": value["image"].title,
                "url": value["image"].file.url if value["image"].file else None,
                "width": value["image"].width,
                "height": value["image"].height,
            }
        
        return {
            "name": value["name"],
            "role": value["role"],
            "image": image_data,
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
        member_block = MemberBlock()
        return {
            "background": value["background"],
            "heading": self.child_blocks["heading"].get_api_representation(
                value["heading"], context
            ),
            "members": [
                member_block.get_api_representation(member, context)
                for member in value["members"]
            ],
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
    
    def get_api_representation(self, value, context=None):
        # Create a StructBlock instance for the items
        item_block = StructBlock([
            ("text", CharBlock()),
        ])
        
        return {
            "list_icon": value["list_icon"],
            "items": [
                {
                    "text": item["text"]
                }
                for item in value["items"]
            ],
        }


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
        imagen_data = None
        if value["imagen"]:
            imagen_data = {
                "id": value["imagen"].id,
                "title": value["imagen"].title,
                "url": value["imagen"].file.url if value["imagen"].file else None,
                "width": value["imagen"].width,
                "height": value["imagen"].height,
            }
        
        return {
            "background": value["background"],
            "imagen": imagen_data,
            "title": self.child_blocks["title"].get_api_representation(
                value["title"], context
            ),
            "description": value["description"],
            "items": self.child_blocks["items"].get_api_representation(
                value["items"], context
            ),
            "badge": self.child_blocks["badge"].get_api_representation(
                value["badge"], context
            ),
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
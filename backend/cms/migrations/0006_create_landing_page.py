from django.db import migrations
from django.utils import timezone
import uuid


def create_landing_page(apps, schema_editor):
    LandingPage = apps.get_model("cms", "LandingPage")
    Page = apps.get_model("wagtailcore", "Page")
    Site = apps.get_model("wagtailcore", "Site")
    ContentType = apps.get_model("contenttypes", "ContentType")
    Locale = apps.get_model("wagtailcore", "Locale")

    if LandingPage.objects.exists():
        return

    root = Page.objects.get(id=1)
    ct = ContentType.objects.get(app_label="cms", model="landingpage")
    locale = Locale.objects.get(language_code="en")

    landing = LandingPage(
        title="Inicio",
        slug="inicio",
        content_type=ct,
        draft_title="Inicio",
        live=True,
        has_unpublished_changes=False,
        show_in_menus=True,
        translation_key=uuid.uuid4(),
        locale=locale,
        first_published_at=timezone.now(),
        last_published_at=timezone.now(),
        body=[
            {
                "type": "hero",
                "value": {
                    "badge": "Integración IoT en el Campo",
                    "title": {
                        "title": "Agricultura de Precisión",
                        "highlight_text": "Inteligente y Sostenible",
                    },
                    "description": "Optimice sus recursos y tome decisiones informadas con nuestro sistema avanzado de monitoreo de variables ambientales en tiempo real, impulsado por sensores IoT de última generación.",
                    "cta_button": {
                        "text": "Comenzar ahora",
                        "icon": "agriculture",
                        "url": "#",
                    },
                },
            },
            {
                "type": "vision_mision",
                "value": {
                    "background": "white",
                    "vision": {
                        "title": "Nuestra Visión",
                        "description": "Ser el referente líder en soluciones de agricultura de precisión en Colombia para el año 2028, transformando el paisaje rural a través de la innovación digital y la conectividad inteligente en el campo.",
                        "icon": "vision",
                    },
                    "mision": {
                        "title": "Nuestra Misión",
                        "description": "Empoderar a los productores agropecuarios mediante herramientas tecnológicas accesibles basadas en sensores IoT y análisis de datos, promoviendo una agricultura más productiva, rentable y respetuosa con el medio ambiente.",
                        "icon": "mission",
                    },
                },
            },
            {
                "type": "two_columns_content",
                "value": {
                    "background": "gray",
                    "left_column": {
                        "title": "Sensores IoT en Tiempo Real",
                        "text": "Implementamos redes de sensores inalámbricos que monitorean humedad del suelo, temperatura ambiente, radiación solar y velocidad del viento. Los datos se transmiten cada 5 minutos a nuestra plataforma en la nube para su análisis inmediato.",
                    },
                    "right_column": {
                        "title": "Decisiones Basadas en Datos",
                        "text": "Nuestros algoritmos de machine learning procesan las variables capturadas por los sensores y generan recomendaciones precisas sobre riego, fertilización y control de plagas, reduciendo el consumo de agua hasta un 40%.",
                    },
                },
            },
            {
                "type": "benefits",
                "value": {
                    "background": "white",
                    "heading": {
                        "title": "Beneficios de la Agricultura Conectada",
                        "text": "Descubra cómo la integración de sensores IoT transforma su operación agrícola",
                    },
                    "items": [
                        {
                            "title": "Monitoreo en Tiempo Real",
                            "description": "Acceda a datos actualizados de temperatura, humedad y otros indicadores clave directamente desde su dispositivo móvil o computador.",
                            "icon": "monitoring",
                        },
                        {
                            "title": "Optimización de Recursos",
                            "description": "Reduzca el consumo de agua y fertilizantes aplicándolos solo cuando y donde se necesiten, basándose en datos precisos de los sensores.",
                            "icon": "optimization",
                        },
                        {
                            "title": "Alertas Inteligentes",
                            "description": "Reciba notificaciones automatizadas ante condiciones críticas como heladas, sequía extrema o detección temprana de plagas.",
                            "icon": "sensor",
                        },
                        {
                            "title": "Eficiencia Operativa",
                            "description": "Automatice la recolección de datos de campo y elimine las inspecciones manuales, ahorrando tiempo y recursos humanos.",
                            "icon": "efficiency",
                        },
                    ],
                },
            },
            {
                "type": "team",
                "value": {
                    "background": "gray",
                    "heading": {
                        "title": "Nuestro Equipo de Expertos",
                        "text": "Profesionales multidisciplinarios comprometidos con la innovación agrícola",
                    },
                    "members": [
                        {
                            "name": "Ing. Juan Carlos Martínez",
                            "role": "Especialista en IoT y Electrónica",
                            "image": None,
                            "description": "Ingeniero Electrónico con más de 12 años de experiencia en implementación de redes de sensores para agricultura de precisión en Colombia.",
                        },
                        {
                            "name": "Dra. María Fernanda López",
                            "role": "Científica de Datos Agrícolas",
                            "image": None,
                            "description": "PhD en Ciencias de la Computación, especializada en machine learning aplicado a la optimización de cultivos y predicción de rendimientos.",
                        },
                        {
                            "name": "Ing. Andrés Pulido",
                            "role": "Desarrollador de Software",
                            "image": None,
                            "description": "Ingeniero de Sistemas experto en desarrollo de plataformas web y móviles para el sector agroindustrial.",
                        },
                    ],
                },
            },
            {
                "type": "feature_highlight",
                "value": {
                    "background": "white",
                    "imagen": None,
                    "title": {
                        "title": "Plataforma de Monitoreo Inteligente",
                        "highlight_text": "Conecte su Cultivo",
                    },
                    "description": "Nuestra plataforma integra datos meteorológicos, de suelo y cultivos en un solo tablero de control. Visualice mapas de calor de humedad, tendencias históricas y reciba recomendaciones generadas por inteligencia artificial para maximizar su producción.",
                    "items": {
                        "list_icon": "check",
                        "items": [
                            {"text": "Estaciones meteorológicas conectadas vía LoRaWAN"},
                            {"text": "Sensores de humedad del suelo multicapa"},
                            {"text": "Alertas personalizables por SMS y correo"},
                            {"text": "Reportes automáticos de rendimiento"},
                            {"text": "Integración con sistemas de riego automatizados"},
                        ],
                    },
                    "badge": {
                        "text": "Tecnología Validada",
                        "status": "success",
                        "icon": "innovation",
                    },
                },
            },
            {
                "type": "cta_section",
                "value": {
                    "background": "green",
                    "heading": {
                        "title": "¿Listo para Transformar su Cultivo con IoT?",
                        "text": "Únase a los más de 500 agricultores que ya están optimizando sus recursos y aumentando su productividad con nuestra plataforma de agricultura de precisión.",
                    },
                    "cta_button": {
                        "text": "Solicitar una Demo",
                        "icon": "play",
                        "url": "#",
                    },
                },
            },
        ],
    )

    from wagtail.models import Page as RealPage

    real_root = RealPage.objects.get(id=1)
    real_root.add_child(instance=landing)

    site = Site.objects.filter(is_default_site=True).first()
    if site:
        site.root_page = landing
        site.save()


class Migration(migrations.Migration):

    dependencies = [
        ("cms", "0005_alter_landingpage_body"),
    ]

    operations = [
        migrations.RunPython(create_landing_page),
    ]

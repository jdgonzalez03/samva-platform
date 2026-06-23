from wagtail import hooks


@hooks.register('register_icons')
def register_icons(icons):
    return icons + [
        'core/icons/tractor.svg',
        'core/icons/organization.svg',
    ]

# Mandatory Leaflet CSS and JS for Wagtail admin, if we use only django-admin, it doesnt need this
@hooks.register('insert_global_admin_css')
def leaflet_admin_css():
    return """
        <link rel="stylesheet" href="/static/leaflet/leaflet.css" />
        <link rel="stylesheet" href="/static/leaflet/leaflet.extras.css" />
        <link rel="stylesheet" href="/static/leaflet/draw/leaflet.draw.css" />
        <style>
            .leaflet-container-default {
                height: 500px !important;
                width: 100% !important;
            }
        </style>
    """

@hooks.register('insert_global_admin_js')
def leaflet_admin_js():
    return """
        <script src="/static/leaflet/leaflet.js"></script>
        <script src="/static/leaflet/draw/leaflet.draw.js"></script>
        <script src="/static/leaflet/leaflet.extras.js"></script>
        <script src="/static/leaflet/leaflet.forms.js"></script>
    """


from wagtail.admin.menu import MenuItem


@hooks.register('register_admin_menu_item')
def register_flower_menu_item():
    return MenuItem(
        'Task Monitor (Flower)',
        'http://localhost:5555',
        icon_name='cogs',
        order=10000,
        attrs={'target': '_blank', 'rel': 'noopener noreferrer'}
    )
# TODO: Add nginx as reverse proxy to serve /tasks/ pointing to
#       the flower container on :5555, removing the localhost dependency
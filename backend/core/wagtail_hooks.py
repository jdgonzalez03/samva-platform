from wagtail import hooks


@hooks.register('register_icons')
def register_icons(icons):
    return icons + [
        'core/icons/tractor.svg',
        'core/icons/organization.svg',
    ]

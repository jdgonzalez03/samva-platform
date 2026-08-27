from django.core.exceptions import ObjectDoesNotExist
from rest_framework.exceptions import NotFound


def get_owned_or_404(queryset, **lookup):
    """Fetch a single row from an ownership-scoped queryset, or raise DRF's generic 404.

    Django's `get_object_or_404` names the model in the response body, which would make a
    row that exists but belongs to someone else distinguishable from one that never existed.
    """
    try:
        return queryset.get(**lookup)
    except ObjectDoesNotExist as does_not_exist:
        raise NotFound from does_not_exist

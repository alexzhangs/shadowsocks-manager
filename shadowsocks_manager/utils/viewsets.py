from django import VERSION as DJANGO_VERSION
from rest_framework.viewsets import ModelViewSet


class CompatModelViewSet(ModelViewSet):
    """
    A compatibility class that extends the ModelViewSet class from Django REST Framework.
    This class provides compatibility for different versions of Django.

    Attributes:
        filter_fields (list): 
            A list of fields to be used for filtering the queryset.
            Used in Django 1.x.
        filterset_fields (list): 
            Used since Django 2.x.
            A list of fields to be used for filtering the queryset.

    Methods:
        __init__(self, *args, **kwargs): Initializes the CompatModelViewSet instance.

    """

    def __init__(self, *args, **kwargs):
        super(CompatModelViewSet, self).__init__(*args, **kwargs)
        if DJANGO_VERSION < (2, 0):
            if not hasattr(self, 'filter_fields') and hasattr(self, 'filterset_fields'):
                self.filter_fields = getattr(self, 'filterset_fields', [])
        else:
            if not hasattr(self, 'filterset_fields') and hasattr(self, 'filter_fields'):
                self.filterset_fields = getattr(self, 'filter_fields', [])

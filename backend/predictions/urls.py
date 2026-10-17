from django.urls import path

from predictions.api import (
    IrrigationDefinitionsAPIView,
    PlotIrrigationPredictionAPIView,
    PredictionModelListAPIView,
)

app_name = "predictions"

urlpatterns = [
    path('models/', PredictionModelListAPIView.as_view(), name='model-list'),
    path(
        'fuzzy/irrigation/definitions/',
        IrrigationDefinitionsAPIView.as_view(),
        name='irrigation-definitions',
    ),
    path(
        'plots/<int:plot_id>/irrigation/',
        PlotIrrigationPredictionAPIView.as_view(),
        name='plot-irrigation',
    ),
]

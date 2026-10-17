from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, pagination, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils import get_owned_or_404
from farm.models import Plot
from predictions.constants import PREDICTION_MODELS
from predictions.fuzzy import membership_definitions
from predictions.serializers import (
    IrrigationPredictionRequestSerializer,
    IrrigationPredictionSerializer,
    MissingSensorDataSerializer,
    PredictionModelSerializer,
)
from predictions.utils import MissingSensorData, create_irrigation_prediction


class PredictionHistoryPagination(pagination.PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50

    def get_paginated_response(self, data):
        # Same envelope as the sensor history: absolute `next`/`previous` URLs would point
        # at the internal docker host, and the client paginates by page number.
        return Response(
            {
                'count': self.page.paginator.count,
                'page': self.page.number,
                'page_size': self.get_page_size(self.request),
                'results': data,
            }
        )


class PredictionModelListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=PredictionModelSerializer(many=True))
    def get(self, request):
        return Response(PredictionModelSerializer(PREDICTION_MODELS, many=True).data)


class IrrigationDefinitionsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        return Response(membership_definitions())


class PlotIrrigationPredictionAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = IrrigationPredictionSerializer
    pagination_class = PredictionHistoryPagination

    def get_plot(self):
        return get_owned_or_404(
            Plot.objects.select_related('farm'),
            pk=self.kwargs['plot_id'],
            farm__owner__user=self.request.user,
        )

    def get_queryset(self):
        return self.get_plot().irrigation_predictions.order_by('-requested_at', '-id')

    @extend_schema(
        request=IrrigationPredictionRequestSerializer,
        responses={
            201: IrrigationPredictionSerializer,
            422: OpenApiResponse(MissingSensorDataSerializer),
        },
    )
    def post(self, request, plot_id):
        plot = self.get_plot()
        params = IrrigationPredictionRequestSerializer(data=request.data)
        params.is_valid(raise_exception=True)

        try:
            prediction = create_irrigation_prediction(plot, params.validated_data['hours'])
        except MissingSensorData as error:
            return Response(
                {'detail': str(error), 'missing': error.missing},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        return Response(
            IrrigationPredictionSerializer(prediction).data,
            status=status.HTTP_201_CREATED,
        )

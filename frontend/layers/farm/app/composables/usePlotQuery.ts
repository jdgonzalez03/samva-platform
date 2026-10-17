import { useQuery } from '@tanstack/vue-query'
import type { Ref } from 'vue'
import { FarmQueryKey } from '../constants/query-keys'
import { farmApi } from '../utils/api/farm'
import { pollUnlessNotFound, retryUnlessNotFound } from '#api/errors'
import { hasTokens } from '#api/tokens'

export const plotQueryOptions = (plotId: Ref<number | null>) => ({
  queryKey: [FarmQueryKey.ROOT, FarmQueryKey.PLOT, plotId] as const,
  queryFn: () => farmApi.getPlot(plotId.value!),
})

export const usePlotQuery = (plotId: Ref<number | null>) =>
  useQuery({
    ...plotQueryOptions(plotId),
    enabled: () => hasTokens() && plotId.value !== null,
    retry: retryUnlessNotFound,
  })

export const plotOverviewQueryOptions = (plotId: Ref<number | null>) => ({
  queryKey: [
    FarmQueryKey.ROOT,
    FarmQueryKey.PLOT,
    plotId,
    FarmQueryKey.OVERVIEW,
  ] as const,
  queryFn: () => farmApi.getPlotOverview(plotId.value!),
})

export const usePlotOverviewQuery = (plotId: Ref<number | null>) =>
  useQuery({
    ...plotOverviewQueryOptions(plotId),
    enabled: () => hasTokens() && plotId.value !== null,
    retry: retryUnlessNotFound,
    refetchInterval: pollUnlessNotFound(LIVE_REFRESH_INTERVAL_MS),
  })

export const plotSummariesQueryOptions = () => ({
  queryKey: [
    FarmQueryKey.ROOT,
    FarmQueryKey.PLOT,
    FarmQueryKey.SUMMARIES,
  ] as const,
  queryFn: () => farmApi.getPlotSummaries(),
})

export const usePlotSummariesQuery = () =>
  useQuery({
    ...plotSummariesQueryOptions(),
    enabled: () => hasTokens(),
    refetchInterval: LIVE_REFRESH_INTERVAL_MS,
  })

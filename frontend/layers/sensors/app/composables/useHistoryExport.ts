import type {
  ExportFormat,
  HistoryQueryFilters,
  SensorSemanticKey,
} from '../types/sensors'
import { sensorsApi } from '../utils/api/sensors'
import { buildExportFilename, parseExportError } from '../utils/history-export'

// Downloads via fetch + Blob instead of a plain `<a href>` link: the export
// endpoint requires the Bearer token, which a browser navigation can't send.
export const useHistoryExport = () => {
  const { t, locale } = useI18n()
  const toast = useToast()

  const isExporting = shallowRef(false)
  const exportError = shallowRef<string | null>(null)

  const formatCount = (value: number): string =>
    new Intl.NumberFormat(locale.value).format(value)

  const clearExportError = (): void => {
    exportError.value = null
  }

  const describeFailure = async (error: unknown): Promise<string> => {
    const payload = await parseExportError(error)
    if (
      payload?.code === 'export_too_large' &&
      payload.count !== undefined &&
      payload.limit !== undefined
    ) {
      return t('sensors.history.export.tooLarge', {
        count: formatCount(payload.count),
        limit: formatCount(payload.limit),
      })
    }
    return t('sensors.history.export.error')
  }

  const exportHistory = async (
    fileFormat: ExportFormat,
    farmId: number,
    farmName: string,
    filters: HistoryQueryFilters,
  ): Promise<void> => {
    if (isExporting.value) return

    isExporting.value = true
    exportError.value = null

    try {
      const query: Record<string, string | number | undefined> = {
        plot: filters.plot,
        variable: filters.variable as SensorSemanticKey | undefined,
        date_from: filters.date_from,
        date_to: filters.date_to,
      }
      const blob = await sensorsApi.getHistoryExport(farmId, fileFormat, query)
      downloadBlob(
        blob,
        buildExportFilename(
          farmName,
          fileFormat,
          filters.date_from,
          filters.date_to,
        ),
      )
      toast.add({
        title: t('sensors.history.export.done'),
        color: 'success',
        icon: 'i-lucide-download',
      })
    } catch (error) {
      // The message also lands in an inline `role="alert"` next to the button:
      // a toast alone can be missed, and the row cap needs an actionable
      // explanation that stays on screen.
      const message = await describeFailure(error)
      exportError.value = message
      toast.add({
        title: t('sensors.history.export.errorTitle'),
        description: message,
        color: 'error',
        icon: 'i-lucide-triangle-alert',
      })
    } finally {
      isExporting.value = false
    }
  }

  return { exportHistory, isExporting, exportError, clearExportError }
}

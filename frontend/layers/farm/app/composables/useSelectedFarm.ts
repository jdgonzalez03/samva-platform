import { getStoredFarmId, setStoredFarmId } from '../utils/selected-farm'

export const useSelectedFarm = () => {
  // useState rather than a module-scoped ref: the latter is a singleton shared
  // across SSR requests.
  const selectedFarmId = useState<number | null>('farm:selectedId', () => null)
  const farmsQuery = useFarmsQuery()

  const farms = computed(() => farmsQuery.data.value ?? [])
  const selectedFarm = computed(
    () => farms.value.find((farm) => farm.id === selectedFarmId.value) ?? null,
  )

  const selectFarm = (farmId: number) => {
    selectedFarmId.value = farmId
    setStoredFarmId(farmId)
  }

  // Reconciling the selection against the list the backend actually returned
  // covers first load, reload (stored id), user switch and deleted farms with
  // one rule, and stays idempotent across the components that call this.
  watch(
    farms,
    (list) => {
      if (!list.length) {
        selectedFarmId.value = null
        return
      }
      if (list.some((farm) => farm.id === selectedFarmId.value)) return

      const storedFarmId = getStoredFarmId()
      selectedFarmId.value =
        list.find((farm) => farm.id === storedFarmId)?.id ?? list[0]!.id
    },
    { immediate: true },
  )

  const refetchFarms = (): void => {
    void farmsQuery.refetch()
  }

  return {
    farms,
    selectedFarm,
    selectFarm,
    isPending: farmsQuery.isPending,
    isError: farmsQuery.isError,
    refetchFarms,
  }
}

import type { ComputedRef, MaybeRefOrGetter } from 'vue'
import { VARIABLE_COLORS } from '../constants/history'
import type { SensorSemanticKey } from '../types/sensors'

// Selected per mode, never an automatic flip: the light step falls outside the
// dark lightness band and loses its contrast against the dark surface.
export function useVariableColor(
  semanticKey: MaybeRefOrGetter<SensorSemanticKey>,
): ComputedRef<string> {
  const colorMode = useColorMode()

  return computed(() => {
    const mode = colorMode.value === 'dark' ? 'dark' : 'light'
    return VARIABLE_COLORS[toValue(semanticKey)][mode]
  })
}

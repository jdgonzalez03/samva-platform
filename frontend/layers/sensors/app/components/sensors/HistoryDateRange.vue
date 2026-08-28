<script setup lang="ts">
import { getLocalTimeZone, parseDate, today } from '@internationalized/date'
import type { DateRange } from 'reka-ui'
import { parseCalendarDate } from '../../utils/history-filters'

const props = defineProps<{
  from: string | null
  to: string | null
}>()

const emit = defineEmits<{ 'update:range': [from: string, to: string] }>()

const { t, locale } = useI18n()

const isCalendarOpen = shallowRef(false)

const maxValue = computed(() => today(getLocalTimeZone()))
const maxDate = computed(() => maxValue.value.toString())

const toDateRange = (): DateRange => ({
  start: props.from ? parseDate(props.from) : undefined,
  end: props.to ? parseDate(props.to) : undefined,
})

// A local draft rather than a controlled `v-model` on the props: a range is
// picked in two clicks, and rejecting the half-finished value would snap the
// calendar back and make the first click look like it did nothing.
// `shallowRef`, not `ref`: deep unwrapping would rewrite the `DateValue` class
// instances into structurally-mapped objects that the calendar's own props no
// longer accept. Both controls replace the whole range object anyway.
const draft = shallowRef<DateRange>(toDateRange())

const typedFrom = shallowRef(props.from ?? '')
const typedTo = shallowRef(props.to ?? '')

watch(
  () => [props.from, props.to],
  () => {
    draft.value = toDateRange()
    typedFrom.value = props.from ?? ''
    typedTo.value = props.to ?? ''
  },
)

watch(draft, (next) => {
  if (!next?.start || !next?.end) return

  const from = next.start.toString()
  const to = next.end.toString()
  if (from === props.from && to === props.to) return

  emit('update:range', from, to)
  isCalendarOpen.value = false
})

// Committed on `change`, not on every keystroke: a native date input reports an
// empty value until every segment is filled, and reacting in between would push
// half-typed days into the URL.
const commitTyped = (): void => {
  const from = parseCalendarDate(typedFrom.value)
  const to = parseCalendarDate(typedTo.value)
  if (!from || !to) return
  if (from === props.from && to === props.to) return

  emit('update:range', from, to)
}

const dateFormatter = computed(
  () => new Intl.DateTimeFormat(locale.value, { dateStyle: 'medium' }),
)

const selectedLabel = computed(() => {
  if (!props.from || !props.to) return null
  return t('sensors.history.range.between', {
    from: dateFormatter.value.format(
      parseDate(props.from).toDate(getLocalTimeZone()),
    ),
    to: dateFormatter.value.format(
      parseDate(props.to).toDate(getLocalTimeZone()),
    ),
  })
})

const triggerLabel = computed(
  () => selectedLabel.value ?? t('sensors.history.range.pick'),
)

// The accessible name keeps a stable prefix while still containing the visible
// label, which would otherwise change with every pick and leave the control
// nameless to anyone looking for it (2.5.3).
const triggerName = computed(() =>
  selectedLabel.value
    ? t('sensors.history.range.pickWith', { range: selectedLabel.value })
    : t('sensors.history.range.pick'),
)
</script>

<template>
  <div class="flex flex-wrap items-end gap-2">
    <!-- Typed entry exists so the calendar is never the only way in (2.1.1).
         Two native date inputs, not `UInputDate`: Reka splits that control into
         `role="spinbutton"` segments carrying hardcoded English labels ("day,",
         "month,") and points `UFormField`'s `for` at a hidden input, so the
         visible label names nothing focusable. A native `<input type="date">`
         is one control the label owns, and the browser announces its parts in
         the user's own language (1.3.1, 3.3.2, 4.1.2).
         `color-scheme` so the built-in picker glyph inverts with the theme
         instead of staying dark on a dark field (1.4.11). -->
    <UFormField :label="t('sensors.history.range.from')">
      <UInput
        v-model="typedFrom"
        type="date"
        :max="maxDate"
        class="dark:scheme-dark"
        @change="commitTyped"
      />
    </UFormField>

    <UFormField :label="t('sensors.history.range.to')">
      <UInput
        v-model="typedTo"
        type="date"
        :max="maxDate"
        class="dark:scheme-dark"
        @change="commitTyped"
      />
    </UFormField>

    <!-- `modal` is what makes Reka trap focus inside the popover and hand it
         back to the trigger on Escape (2.1.2). -->
    <UPopover v-model:open="isCalendarOpen" modal>
      <UButton
        icon="i-lucide-calendar"
        color="neutral"
        variant="subtle"
        :label="triggerLabel"
        :aria-label="triggerName"
        class="min-h-8"
      />

      <template #content>
        <section class="p-2" :aria-label="t('sensors.history.range.calendar')">
          <!-- Reka names the grid "Event Date" by default; the prop is the only
               way to get a translated heading on it. -->
          <UCalendar
            v-model="draft"
            range
            :locale="locale"
            :max-value="maxValue"
            :calendar-label="t('sensors.history.range.calendar')"
          />
        </section>
      </template>
    </UPopover>
  </div>
</template>

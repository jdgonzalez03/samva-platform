// Payload formatter (Uplink) para The Things Network — nodo agrícola, payload v2
// fPort 3, 46 bytes, big-endian. Cada sonda va como [id u16][valores…] en este orden:
// aire, foliar, aux, co2, watermark 1-3, suelo, energía.
// Las claves de `readings` son las SemanticKey de SAMVA y el `id` es el serial
// del FieldSensor, así el backend guarda cada sonda sin tabla de mapeo.

var FPORT = 3
var LONGITUD = 46

function decodeUplink(input) {
  var b = input.bytes
  if (input.fPort !== FPORT || b.length < LONGITUD) {
    return {
      errors: [
        'Payload inesperado (fPort ' +
          input.fPort +
          ', ' +
          b.length +
          ' bytes; se espera fPort ' +
          FPORT +
          ', ' +
          LONGITUD +
          ' bytes)',
      ],
    }
  }
  var i = 0
  function u16() {
    var v = (b[i] << 8) | b[i + 1]
    i += 2
    return v
  }
  function s16() {
    var v = u16()
    return v > 32767 ? v - 65536 : v
  }

  var aire = { id: u16(), readings: {} }
  aire.readings.air_temperature = s16() / 100 // °C   SHT30 #1
  aire.readings.relative_humidity = u16() / 100 // %RH

  var foliar = { id: u16(), readings: {} }
  foliar.readings.leaf_temperature = s16() / 100 // °C   MLX90614 objeto
  foliar.readings.air_temperature = s16() / 100 // °C   MLX90614 ambiente

  var aux = { id: u16(), readings: {} }
  aux.readings.air_temperature = s16() / 100 // °C   sonda auxiliar

  var co2 = { id: u16(), readings: {} }
  co2.readings.co2 = u16() // ppm  SEN0159

  var watermarks = []
  for (var k = 0; k < 3; k++) {
    var wm = { id: u16(), readings: {} }
    wm.readings.soil_water_tension = u16() / 10 // kPa
    watermarks.push(wm)
  }

  var suelo = { id: u16(), readings: {} }
  suelo.readings.soil_temperature = s16() / 100 // °C

  var energia = { id: u16(), readings: {} }
  energia.readings.battery_voltage = u16() / 1000 // V    INA3221
  energia.readings.battery_current = s16() // mA (+ carga, - descarga)
  energia.readings.solar_panel_voltage = u16() / 1000 // V
  energia.readings.solar_panel_current = u16() // mA

  var sensors = [aire, foliar, aux, co2]
    .concat(watermarks)
    .concat([suelo, energia])

  return {
    data: {
      sensors: sensors,
      delta_t_hoja_aire:
        Math.round(
          (foliar.readings.leaf_temperature - aire.readings.air_temperature) *
            100,
        ) / 100,
    },
  }
}

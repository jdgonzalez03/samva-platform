# main.py — Nodo agrícola SIMULADO -> LA66 (UART) -> LoRaWAN / The Things Network
# Raspberry Pi Pico 2W + MicroPython
#
# Sensores simulados (mismos del nodo real):
#   SHT30 #1  -> temperatura / humedad del aire
#   SHT30 #2  -> temperatura / humedad auxiliar (compensación de los Watermark)
#   MLX90614  -> temperatura foliar (objeto) y ambiente del sensor
#   SEN0159   -> CO2 (ppm)
#   Watermark 200SS x3 (vía HCF4052) -> tensión hídrica del suelo (kPa / cbar)
#   Sensor de temperatura de suelo
#   INA3221   -> tensión/corriente de batería y de panel solar
#
# Conexión (cruzada, GND común):
#   Pico GP0 (UART0 TX) -> RXD del adaptador LA66
#   Pico GP1 (UART0 RX) <- TXD del adaptador LA66
#   GND ---------------- GND

import math
import random
import struct
import time

import ubinascii
from machine import UART, Pin

# ======================= CONFIGURACIÓN =======================
UART_ID = 0
PIN_TX = 0
PIN_RX = 1
BAUDIOS = 9600  # velocidad por defecto del LA66
FPORT = 3  # payload v2 (un bloque por sonda); el decodificador de TTN rechaza otro puerto
CONFIRMADO = 0  # 0 = sin confirmación (recomendado), 1 = confirmado
INTERVALO_S = 60  # periodo de envío en segundos
HORA_INICIO = 6.0  # hora del día simulada al arrancar (0-24)
ACELERACION = 1  # 1 = tiempo real; 60 = cada minuto real avanza 1 h simulada
DEBUG = True

# ID de cada sonda física: viaja en el payload y es el "serial number" del
# FieldSensor registrado en SAMVA. Únicos en toda la plataforma (u16: 0-65535).
ID_AIRE = 101  # SHT30 #1 / DHT
ID_FOLIAR = 102  # MLX90614
ID_AUX = 103  # sonda auxiliar
ID_CO2 = 104  # SEN0159
ID_WM1 = 105  # Watermark 1
ID_WM2 = 106  # Watermark 2
ID_WM3 = 107  # Watermark 3
ID_SUELO = 108  # temperatura de suelo
ID_ENERGIA = 109  # INA3221
# =============================================================

led = Pin("LED", Pin.OUT)
uart = UART(UART_ID, baudrate=BAUDIOS, tx=Pin(PIN_TX), rx=Pin(PIN_RX), timeout=100)
T0 = time.time()


# ----------------------- Utilidades -----------------------
def rnd():
    """Aleatorio uniforme [0,1) usando solo getrandbits (siempre disponible)."""
    return random.getrandbits(24) / 16777216


def ruido(a):
    return (rnd() * 2 - 1) * a


def limitar(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


def aproximar(actual, objetivo, tau_min, dt_min, r=0.0):
    """Filtro de primer orden: el valor se acerca al objetivo con constante tau."""
    alfa = 1 - math.exp(-dt_min / tau_min)
    return actual + (objetivo - actual) * alfa + ruido(r)


def hora_simulada():
    seg = (time.time() - T0) * ACELERACION
    return (HORA_INICIO + seg / 3600) % 24


# ----------------------- LA66 / AT -----------------------
def leer_uart(espera_ms):
    fin = time.ticks_add(time.ticks_ms(), espera_ms)
    buf = b""
    while time.ticks_diff(fin, time.ticks_ms()) > 0:
        if uart.any():
            buf += uart.read()
        else:
            time.sleep_ms(20)
    try:
        return buf.decode()
    except Exception:
        return str(buf)


def at(cmd, espera_ms=1000):
    if uart.any():
        uart.read()  # limpiar basura previa
    uart.write(cmd + "\r\n")
    r = leer_uart(espera_ms)
    if DEBUG:
        print(">>", cmd)
        if r.strip():
            print("<<", r.strip())
    return r


def esta_unido():
    r = at("AT+NJS=?", 800)
    return any(l.strip() == "1" for l in r.split("\n"))


def unir_red(max_intentos=10):
    for i in range(max_intentos):
        if esta_unido():
            print("✔ Unido a TTN")
            return True
        print("No unido. AT+JOIN (intento %d/%d)" % (i + 1, max_intentos))
        at("AT+JOIN", 1000)
        r = leer_uart(15000)  # el join OTAA puede tardar varios segundos
        if DEBUG and r.strip():
            print("<<", r.strip())
    print("✘ No se logró el join")
    return False


# ----------------------- Simulador del nodo -----------------------
class NodoSimulado:
    def __init__(self):
        self.t_aire, self.h_aire = 23.0, 90.0
        self.t_aux, self.h_aux = 23.0, 92.0
        self.t_hoja, self.t_amb_ir = 22.5, 23.0
        self.co2 = 520.0
        self.wm = [12.0, 18.0, 10.0]  # kPa (tres profundidades/zonas)
        self.t_suelo = 24.5
        self.nubes = 0.3  # 0 = despejado, 1 = cubierto
        self.soc = 0.75  # estado de carga de la batería
        self.v_bat, self.i_bat = 3.95, 0.0
        self.v_pan, self.i_pan = 0.0, 0.0
        self.riegos = 0

    def actualizar(self, h):
        dt = INTERVALO_S * ACELERACION / 60  # minutos simulados por paso

        # Clima base (perfil típico de los Llanos)
        self.nubes = limitar(aproximar(self.nubes, 0.35, 90, dt, 0.05), 0.0, 0.95)
        sol = max(0.0, math.sin(math.pi * (h - 6) / 12))  # 0 de noche
        irr = sol * (1 - 0.7 * self.nubes)  # irradiancia relativa
        ciclo = math.cos(2 * math.pi * (h - 15) / 24)  # +1 a las 15h, -1 a las 3h

        # SHT30 #1 — aire
        t_obj = 26.5 + 5.0 * ciclo + 2.0 * (irr - 0.4 * sol)
        self.t_aire = limitar(aproximar(self.t_aire, t_obj, 20, dt, 0.08), 15, 40)
        h_obj = 78 - 18 * ciclo - 6 * irr
        self.h_aire = limitar(aproximar(self.h_aire, h_obj, 25, dt, 0.4), 35, 99.5)

        # SHT30 #2 — cerca del suelo / sombreado (más húmedo y estable)
        self.t_aux = limitar(aproximar(self.t_aux, self.t_aire - 1.2, 35, dt, 0.05), 15, 38)
        self.h_aux = limitar(aproximar(self.h_aux, self.h_aire + 5, 35, dt, 0.3), 40, 99.9)

        # Watermark — secado por evapotranspiración, riego al superar umbral
        prof = (1.0, 0.7, 0.45)
        for k in range(3):
            et = 0.012 * (0.15 + irr) * (1 + (self.t_aire - 25) / 20) * (1 + self.wm[k] / 40)
            self.wm[k] = limitar(self.wm[k] + et * prof[k] * dt + ruido(0.15), 0, 239)
        if sum(self.wm) / 3 > 60:  # evento de riego simulado
            self.wm = [8 + rnd() * 4, 12 + rnd() * 5, 9 + rnd() * 4]
            self.riegos += 1

        # MLX90614 — hoja: más fría que el aire si hay agua, más caliente con estrés
        estres = limitar((sum(self.wm) / 3 - 20) / 50, 0, 1)
        delta = irr * (-2.0 + 5.0 * estres) - (1 - sol) * 0.8
        self.t_hoja = aproximar(self.t_hoja, self.t_aire + delta, 5, dt, 0.15)
        self.t_amb_ir = aproximar(self.t_amb_ir, self.t_aire + 0.6 * irr, 10, dt, 0.05)

        # SEN0159 — CO2 alto de noche (respiración), baja con fotosíntesis
        co2_obj = 430 + 110 * (1 - sol) - 25 * irr
        self.co2 = limitar(aproximar(self.co2, co2_obj, 30, dt, 8), 380, 900)

        # Temperatura de suelo — amplitud menor y desfase
        ts_obj = 25.5 + 2.0 * math.cos(2 * math.pi * (h - 17) / 24)
        self.t_suelo = aproximar(self.t_suelo, ts_obj, 120, dt, 0.02)

        # INA3221 — panel, MPPT y batería 2x18650 en paralelo (5000 mAh)
        if irr > 0.03:
            self.v_pan = 5.8 + 0.8 * irr + ruido(0.05)
            self.i_pan = limitar(750 * irr + ruido(10), 0, 900)  # mA
        else:
            self.v_pan = 0.15 + rnd() * 0.2
            self.i_pan = 0.0
        consumo = 45 + ruido(5)  # mA del nodo
        carga = self.i_pan * self.v_pan * 0.85 / max(self.v_bat, 3.0)
        if self.soc >= 0.99:
            carga = min(carga, consumo)  # cargador en flotación
        self.i_bat = carga - consumo  # + carga, - descarga
        self.soc = limitar(self.soc + self.i_bat * (dt / 60) / 5000, 0.05, 1.0)
        self.v_bat = 3.40 + 0.80 * self.soc + 0.0002 * self.i_bat + ruido(0.005)

        return {
            "t_aire": self.t_aire,
            "h_aire": self.h_aire,
            "t_aux": self.t_aux,
            "h_aux": self.h_aux,
            "t_hoja": self.t_hoja,
            "t_amb_ir": self.t_amb_ir,
            "co2": self.co2,
            "wm1": self.wm[0],
            "wm2": self.wm[1],
            "wm3": self.wm[2],
            "t_suelo": self.t_suelo,
            "v_bat": self.v_bat,
            "i_bat": self.i_bat,
            "v_pan": self.v_pan,
            "i_pan": self.i_pan,
        }


# ----------------------- Codificación v2 (46 bytes, big-endian) -----------------------
# Cada sonda va como [id u16][valores...]:
#   aire    H h H        id, temp_aire s16/100, hum_aire u16/100
#   foliar  H h h        id, temp_foliar s16/100, temp_amb_ir s16/100
#   aux     H h          id, temp_aux s16/100
#   co2     H H          id, co2 u16 ppm
#   wm1..3  H H (x3)     id, tensión u16/10 kPa
#   suelo   H h          id, temp_suelo s16/100
#   energía H H h H H    id, v_bat u16/1000, i_bat s16 mA, v_pan u16/1000, i_pan u16 mA
# h_aux se sigue simulando pero no se envía.
FORMATO = ">HhHHhhHhHHHHHHHHHhHHhHH"


def codificar(d):
    return struct.pack(
        FORMATO,
        ID_AIRE,
        int(round(d["t_aire"] * 100)),
        int(round(d["h_aire"] * 100)),
        ID_FOLIAR,
        int(round(d["t_hoja"] * 100)),
        int(round(d["t_amb_ir"] * 100)),
        ID_AUX,
        int(round(d["t_aux"] * 100)),
        ID_CO2,
        int(round(d["co2"])),
        ID_WM1,
        int(round(d["wm1"] * 10)),
        ID_WM2,
        int(round(d["wm2"] * 10)),
        ID_WM3,
        int(round(d["wm3"] * 10)),
        ID_SUELO,
        int(round(d["t_suelo"] * 100)),
        ID_ENERGIA,
        int(round(d["v_bat"] * 1000)),
        int(round(d["i_bat"])),
        int(round(d["v_pan"] * 1000)),
        int(round(d["i_pan"])),
    )


def mostrar(d, h):
    print("\n--- Hora simulada %02d:%02d ---" % (int(h), int((h % 1) * 60)))
    print(
        "Aire  %.2f °C  %.1f %%   | Aux %.2f °C  %.1f %%"
        % (d["t_aire"], d["h_aire"], d["t_aux"], d["h_aux"])
    )
    print("Hoja  %.2f °C  (amb IR %.2f °C) | CO2 %d ppm" % (d["t_hoja"], d["t_amb_ir"], d["co2"]))
    print(
        "WM    %.1f / %.1f / %.1f kPa | Suelo %.2f °C"
        % (d["wm1"], d["wm2"], d["wm3"], d["t_suelo"])
    )
    print(
        "Bat   %.3f V  %+d mA | Panel %.2f V  %d mA"
        % (d["v_bat"], d["i_bat"], d["v_pan"], d["i_pan"])
    )


# ----------------------- Programa principal -----------------------
def main():
    time.sleep(2)
    at("AT", 500)
    unir_red()

    nodo = NodoSimulado()
    proximo = time.time()
    while True:
        h = hora_simulada()
        d = nodo.actualizar(h)
        payload = codificar(d)
        hexa = ubinascii.hexlify(payload).decode()
        if DEBUG:
            mostrar(d, h)

        if not esta_unido():
            unir_red(3)

        led.on()
        at("AT+SENDB=%d,%d,%d,%s" % (CONFIRMADO, FPORT, len(payload), hexa), 3000)
        led.off()

        proximo += INTERVALO_S
        espera = proximo - time.time()
        if espera > 0:
            time.sleep(espera)
        else:
            proximo = time.time()


main()

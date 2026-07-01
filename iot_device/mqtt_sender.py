import json
import time
import random
import paho.mqtt.client as mqtt

# ── CONFIGURACIÓN ─────────────────────────────────────────────
BROKER      = "test.mosquitto.org"  # ✅ mismo que Godot
PORT        = 1883
INTERVALO   = 10
ESTACION_ID = 1

TOPIC = f"fisi/smat/estaciones/{ESTACION_ID}/lecturas"

# ── Cliente MQTT ──────────────────────────────────────────────
client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"[MQTT] ✅ Conectado a {BROKER}:{PORT}")
        print(f"[MQTT] Publicando en: {TOPIC}")
    else:
        print(f"[MQTT] ❌ Error de conexión. Código: {rc}")

client.on_connect = on_connect
client.connect(BROKER, PORT)
client.loop_start()

print("🚀 Simulador IoT SMAT — Estación 1")
print(f"   Broker   : {BROKER}:{PORT}")
print(f"   Tópico   : {TOPIC}")
print(f"   Intervalo: {INTERVALO} s\n")

while True:
    valor = round(random.uniform(5.0, 85.0), 2)
    payload = {
        "valor": valor,
        "estacion_id": ESTACION_ID,
        "timestamp": time.time(),
    }
    result = client.publish(TOPIC, json.dumps(payload), qos=1)
    estado = "✓" if result.rc == 0 else f"✗ rc={result.rc}"
    alerta = "🟢 NORMAL" if valor < 50 else "🔴 ALERTA"
    print(f"📡 [{estado}] valor={valor}  {alerta}")
    print(f"⏱  Próxima lectura en {INTERVALO} s...\n")
    time.sleep(INTERVALO)
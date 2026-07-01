import sys
import json
import time
import requests
import paho.mqtt.client as mqtt
import os

# ── CONFIGURACIÓN ─────────────────────────────────────────────
API_URL     = os.environ.get("API_URL", "http://localhost:8000")
MQTT_BROKER = "test.mosquitto.org"
MQTT_PORT   = 1883
MQTT_TOPIC  = "fisi/smat/estaciones/+/lecturas"   # '+' escucha TODAS las estaciones
USERNAME  = "yo"
PASSWORD  = "123456"

# ── UMBRALES DE FILTRADO ──────────────────────────────────────
UMBRAL_VARIACION = 0.05   # 5 % de cambio mínimo para enviar
HEARTBEAT_SEG    = 60     # enviar de todas formas si pasan ≥ 60 s

# ── CACHÉ por estación: {estacion_id: {"valor": float, "ts": float}} ──
cache: dict[int, dict] = {}

# ── TOKEN JWT ─────────────────────────────────────────────────
JWT_TOKEN: str | None = None

def obtener_token():
    global JWT_TOKEN
    try:
        resp = requests.post(
            f"{API_URL}/token",
            data={"username": USERNAME, "password": PASSWORD},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if resp.status_code == 200:
            JWT_TOKEN = resp.json()["access_token"]
            print("[AUTH] ✅ Token obtenido correctamente.")
        else:
            print(f"[AUTH ERROR] ❌ Código {resp.status_code}")
    except Exception as e:
        print(f"[AUTH CRÍTICO] Sin conexión al servidor: {e}")
        sys.exit(1)

# ── LÓGICA DE FILTRADO ────────────────────────────────────────
def debe_enviar(estacion_id: int, nuevo_valor: float) -> tuple[bool, str]:
    """
    Devuelve (True, motivo) si la lectura debe enviarse a FastAPI,
    (False, motivo) si debe bloquearse.
    """
    ahora = time.time()

    if estacion_id not in cache:
        return True, "primera lectura"

    ultimo = cache[estacion_id]
    valor_ant = ultimo["valor"]
    ts_ant    = ultimo["ts"]

    # 1. Heartbeat: han pasado ≥ 60 s → enviar siempre
    segundos_desde_ultimo = ahora - ts_ant
    if segundos_desde_ultimo >= HEARTBEAT_SEG:
        return True, f"heartbeat ({segundos_desde_ultimo:.0f} s transcurridos)"

    # 2. Variación significativa: |Δ| > 5 %
    if valor_ant == 0:
        variacion = 1.0  # evitar div/0
    else:
        variacion = abs(nuevo_valor - valor_ant) / abs(valor_ant)

    if variacion > UMBRAL_VARIACION:
        return True, f"variación {variacion*100:.1f}% (umbral 5%)"

    return False, f"bloqueado — variación {variacion*100:.1f}% < 5%, {segundos_desde_ultimo:.0f}s < {HEARTBEAT_SEG}s"

# ── CALLBACKS MQTT ────────────────────────────────────────────
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("🟢 Conectado al Broker MQTT")
        client.subscribe(MQTT_TOPIC)
        print(f"📡 Escuchando: {MQTT_TOPIC}")
    else:
        print(f"🔴 Error de conexión MQTT. Código: {rc}")
        sys.exit(1)

def on_message(client, userdata, msg):
    try:
        payload_raw = msg.payload.decode("utf-8")
        data_json   = json.loads(payload_raw)

        # Extraer ID de estación desde el tópico  fisi/smat/estaciones/{id}/lecturas
        topic_parts = msg.topic.split("/")
        estacion_id = int(topic_parts[3])
        nuevo_valor = float(data_json["valor"])

        print(f"\n📩 MQTT [{estacion_id}] recibido: valor={nuevo_valor}")

        # ── Aplicar filtro ──────────────────────────────────
        enviar, motivo = debe_enviar(estacion_id, nuevo_valor)

        if not enviar:
            print(f"🚫 HTTP bloqueado  → {motivo}")
            return

        # ── Enviar a FastAPI ────────────────────────────────
        api_payload = {"valor": nuevo_valor, "estacion_id": estacion_id}
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {JWT_TOKEN}",
        }

        resp = requests.post(
            f"{API_URL}/lectura/",
            json=api_payload,
            headers=headers,
            timeout=5,
        )

        if resp.status_code in (200, 201):
            # Actualizar caché
            cache[estacion_id] = {"valor": nuevo_valor, "ts": time.time()}
            print(f"💾 GUARDADO   → {motivo} | valor={nuevo_valor} | estación={estacion_id}")
        else:
            print(f"⚠️  API rechazó | código={resp.status_code} | {resp.text[:80]}")

    except KeyError as e:
        print(f"❌ Clave faltante en payload: {e}")
    except ValueError:
        print("❌ Error de tipo: valor o ID no numéricos")
    except Exception as e:
        print(f"❌ Error crítico en el Bridge: {e}")

# ── INICIALIZACIÓN ────────────────────────────────────────────
print("🚀 Inicializando Bridge SMAT con filtro de redundancia...")
obtener_token()

bridge_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
bridge_client.on_connect = on_connect
bridge_client.on_message = on_message

try:
    bridge_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    bridge_client.loop_forever()
except KeyboardInterrupt:
    print("\n🛑 Bridge detenido por el administrador.")
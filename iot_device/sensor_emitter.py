import requests
import random
import time

# ── Configuración ─────────────────────────────────────────────
API_URL    = "http://localhost:8000"
ESTACION_ID = 1
USERNAME   = "yo"
PASSWORD   = "123456"
INTERVALO  = 5  # segundos entre lecturas

# ── Obtener token automáticamente (evita tokens expirados) ────
def obtener_token():
    try:
        response = requests.post(
            f"{API_URL}/token",
            data={"username": USERNAME, "password": PASSWORD},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if response.status_code == 200:
            token = response.json()["access_token"]
            print(f"[AUTH] Token obtenido correctamente.")
            return token
        else:
            print(f"[AUTH ERROR] No se pudo obtener token: {response.status_code}")
            return None
    except Exception as e:
        print(f"[AUTH CRÍTICO] Sin conexión al servidor: {e}")
        return None

# ── Simula la lectura del sensor físico ───────────────────────
def leer_sensor_emulado():
    return round(random.uniform(10.5, 85.0), 2)

# ── Bucle principal de emisión ────────────────────────────────
def enviar_telemetria():
    print(f"--- Iniciando Emisor IoT para Estación {ESTACION_ID} ---")

    token = obtener_token()
    if not token:
        print("[ABORTADO] No se pudo autenticar. Verifica usuario y contraseña.")
        return

    intentos_fallidos = 0

    while True:
        valor = leer_sensor_emulado()
        payload = {"valor": valor, "estacion_id": ESTACION_ID}
        headers = {"Authorization": f"Bearer {token}"}

        try:
            response = requests.post(
                f"{API_URL}/lectura/",   # ← endpoint correcto
                json=payload,
                headers=headers,
            )

            if response.status_code in (200, 201):
                # Indicador visual: verde (<50) o rojo (>=50)
                alerta = "🟢 NORMAL" if valor < 50 else "🔴 ALERTA"
                print(f"[OK] Lectura enviada: {valor} cm  {alerta}")
                intentos_fallidos = 0

            elif response.status_code == 401:
                # Token expirado → renovar automáticamente
                print("[TOKEN] Expirado, renovando...")
                token = obtener_token()
                if not token:
                    print("[ABORTADO] No se pudo renovar el token.")
                    break

            else:
                print(f"[ERROR] Código: {response.status_code} → {response.text}")
                intentos_fallidos += 1

        except Exception as e:
            print(f"[CRÍTICO] Sin conexión con el servidor: {e}")
            intentos_fallidos += 1

        # Si falla 5 veces seguidas, detener el emisor
        if intentos_fallidos >= 5:
            print("[ABORTADO] Demasiados errores consecutivos. Deteniendo emisor.")
            break

        time.sleep(INTERVALO)


if __name__ == "__main__":
    enviar_telemetria()
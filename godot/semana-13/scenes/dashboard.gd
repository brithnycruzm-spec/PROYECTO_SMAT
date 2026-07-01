extends Node2D

@onready var mqtt = $MQTTClient

const BROKER = "ws://test.mosquitto.org:8080/mqtt"
const TOPICO = "fisi/smat/estaciones/+/lecturas"

func _ready():
	print("[DASHBOARD] Conectando a ", BROKER)
	mqtt.connect_to_broker(BROKER)
	mqtt.broker_connected.connect(_on_connected)
	mqtt.broker_disconnected.connect(_on_disconnected)
	mqtt.broker_connection_failed.connect(_on_connection_failed)
	mqtt.received_message.connect(_on_msg)

func _on_connected():
	print("[DASHBOARD] ✅ Conectado. Suscribiendo a: ", TOPICO)
	mqtt.subscribe(TOPICO)

func _on_disconnected():
	print("[DASHBOARD] ⚠️ Desconectado del broker")

func _on_connection_failed():
	print("[DASHBOARD] ❌ Falló la conexión al broker")

func _on_msg(topic: String, message: String):
	print("[DASHBOARD] Mensaje | tópico: ", topic, " | payload: ", message)

	var data = JSON.parse_string(message)
	if data == null:
		print("[ERROR] JSON inválido: ", message)
		return

	var partes = topic.split("/")
	if partes.size() < 4:
		print("[ERROR] Tópico inesperado: ", topic)
		return

	var id    = partes[3]
	var valor = data.get("valor", null)
	if valor == null:
		print("[ERROR] Payload sin campo 'valor'")
		return

	actualizar_sensor(id, valor)

func actualizar_sensor(id: String, valor):
	# Estacion_1 es hijo directo del nodo principal Dashboard
	var nodo = get_node_or_null("Estacion_" + str(id))
	if nodo:
		nodo.actualizar_estado(valor)
		print("[DASHBOARD] Estacion_", id, " → valor: ", valor)
	else:
		print("[DASHBOARD] ⚠️ Nodo no encontrado: Estacion_", id)

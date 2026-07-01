extends Node2D

func actualizar_estado(valor):
	$Label.text = str(valor) + " cm"
	# Lógica de color
	if valor > 70:
		$Sprite2D.modulate = Color.RED
	else:
		$Sprite2D.modulate = Color.GREEN

def analyze_dc(voltage_v, resistance_ohm):
	if resistance_ohm <= 0:
		raise ValueError("Resistance must be positive")
	current_a = voltage_v / resistance_ohm
	power_w = voltage_v * current_a
	return {"current_a": current_a, "power_w": power_w}


if __name__ == "__main__":
	voltage_v = float(input("Voltage (V): "))
	resistance_ohm = float(input("Resistance (ohm): "))
	print(analyze_dc(voltage_v, resistance_ohm))

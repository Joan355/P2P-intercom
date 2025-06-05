import subprocess
import platform

# Configura aquí:
script_a_ejecutar = "python3 D:\\python\\libro\\just_practicing\\peer2peer\\main.py"  # Cambia a tu script real
n = 5  # Número de veces que quieres ejecutarlo

sistema = platform.system()

for i in range(n):
    if sistema == "Linux":
        # Intenta con gnome-terminal, puedes cambiar a xterm o konsole si usas otro entorno
        subprocess.Popen(["gnome-terminal", "--", "bash", "-c", f"{script_a_ejecutar}; exec bash"])
    elif sistema == "Darwin":
        # macOS usa osascript para abrir Terminal.app
        subprocess.Popen([
            "osascript", "-e",
            f'tell application "Terminal" to do script "{script_a_ejecutar}"'
        ])
    elif sistema == "Windows":
        # Ejecuta en nuevas ventanas de cmd
        subprocess.Popen([
            "cmd.exe", "/c", f"start cmd.exe /k {script_a_ejecutar}"
        ])
    else:
        print("Sistema operativo no soportado")

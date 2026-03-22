import time
import sys
import tty
import termios
from rich.console import Console
from rich.align import Align
from rich.panel import Panel
from rich.live import Live
from rich import box
from rich.text import Text

console = Console()

LYRICS = [
    ("We're no strangers to love", 2.0),
    ("You know the rules and so do I", 2.0),
    ("A full commitment's what I'm thinking of", 2.5),
    ("You wouldn't get this from any other guy", 2.5),
    ("", 0.5),
    ("I just wanna tell you how I'm feeling", 2.5),
    ("Gotta make you understand", 1.5),
    ("", 0.5),
    ("Never gonna give you up", 1.5),
    ("Never gonna let you down", 1.5),
    ("Never gonna run around and desert you", 2.5),
    ("Never gonna make you cry", 1.5),
    ("Never gonna say goodbye", 1.5),
    ("Never gonna tell a lie and hurt you", 2.5),
]

RICK_ASCII = """
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠿⢿⠿⠷⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡟⠛⠉⠀⠀⠀⠐⠒⠒⠒⠺⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠏⡰⠃⠄⠀⠀⠀⠀⠆⠀⠀⢢⠈⠻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠏⣐⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠈⠂⠙⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠉⢉⡄⢱⣿⣿⣿⣾⣿⣿⣷⣦⡀⠀⢀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⢸⡇⠸⣿⣿⣿⣿⣿⣿⣿⣿⣧⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣏⠂⣀⡜⠁⠀⠂⠀⢹⣯⠉⠉⠛⠻⠏⠀⣼⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡏⠀⢻⡇⢸⣿⣷⣆⣸⣿⣷⣶⣶⣿⠀⠼⣻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⠀⢸⡇⣸⣿⠟⣀⣠⣈⣿⣻⣿⡿⠀⢰⣭⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠶⠾⠁⣿⣥⣅⣉⣛⣛⠛⣩⠗⢁⣀⣼⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡃⠠⡌⠻⣿⣿⣷⣿⣿⡏⢰⣿⣿⣿⣟⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠏⠀⣦⣍⣀⣈⣉⣡⣊⡅⠈⢴⣶⣭⣛⣿⣻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⢃⡄⡄⢿⣿⣿⣿⣿⣿⡿⢁⡇⠀⠙⠿⣿⣷⡽⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⡿⠿⠘⢰⣿⡇⠓⠚⠻⢿⣿⠿⢋⣴⣿⠁⠀⠀⠀⠀⠀⠈⠑⠛⠛⠻⠿⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⡿⢟⡫⠉⠉⠀⠀⠀⣿⣿⣼⣿⣯⠁⠘⢁⣴⢿⣿⠟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⠋⠁⠒⠉⠀⠀⠀⠀⠀⢳⣿⠿⡟⣿⣿⠘⢰⣷⣿⣿⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢹⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠰⡇⣿⣿⠠⠤⢬⣉⣉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⣿⠃⠘⠒⠲⠤⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢰⣿⡷⢠⢉⣈⡓⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠠⣿⣿⣿⣿⣿⣿⣿⣿⣿
⡏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣺⣿⡇⠤⢤⣭⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⣿⣿⣿⣿⣿⣿⣿⣿
⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣸⣿⡇⠒⠶⠖⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠻⢿⣿⣿⣿⣿⣿
⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣼⣿⢉⣉⣉⠁⠀⠀⠀⠀⠐⠒⠶⣶⣶⣶⣤⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⠿⣿⣿⣿
⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢼⣿⠠⠤⣌⠀⠀⠀⠀⠀⠰⠉⣴⣶⣶⣿⣿⣿⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠻⣿
⣷⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠺⣸⠐⠲⠄⠀⠀⠀⠀⠀⠀⠈⣿⠛⠛⣛⣿⣿⣿⡆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿
⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣹⣿⠈⠒⠂⠀⠀⠀⠀⠀⠀⠀⠘⠚⠛⠻⠿⣿⣿⣷⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢿
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢼⣽⠀⢉⡁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⠿⠏⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸
⠄⠀⠀⠀⣠⣤⠶⠿⢿⣻⣄⠀⠀⡼⣿⠀⠤⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣸
⣾⠀⠀⠜⠁⢼⣶⣯⣤⣤⡴⠀⠀⢹⡟⠐⠒⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣀⡀⠀⠀⠀⣀⣀⣀⣀⣴⣿⣿
⣿⡄⠀⠀⠀⠀⢿⣦⣤⠤⠒⠀⠀⣸⡏⠀⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣶⣄⡀⠀⠘⠒⠖⠒⠀⠀⠀⢹⣷⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣦⣄⣀⡀⠀⠀⠀⠀⢸⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⠁⠀⠀⠀⣤⣼⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⡟⠀⠀⠀⠀⣿⣿⢿⣷⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
"""

def getch():
    """Obtiene un solo caracter del input estándar en Linux/macOS sin esperar a Enter."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def run():
    console.clear()
    
    # Animación de carga "Fake Hacker"
    steps = [
        "Inicializando protocolos legacy...",
        "Bypasseando mainframe de seguridad...",
        "Inyectando payload en la memoria...",
        "Accediendo al núcleo pleistocénico...",
        "Sobrescribiendo lógica de sentido común..."
    ]
    
    with Live(console=console, refresh_per_second=10) as live:
        for step in steps:
            live.update(Align.center(f"[bold red blink]{step}[/bold red blink]"))
            time.sleep(0.9)
        
        live.update(Align.center("[bold green]ACCESO CONCEDIDO: MODO RICK[/bold green]"))
        time.sleep(1)

    console.clear()
    time.sleep(0.5)

    # Modo Karaoke
    for line, duration in LYRICS:
        if not line:
            console.print()
        else:
            # Un toque de color para el estribillo
            style = "bold cyan" if "Never gonna" not in line else "bold magenta"
            console.print(Align.center(f"[{style}]♫ {line} ♫[/{style}]"))
        time.sleep(duration)

    console.print("\n" * 2)

    # El marco para tu ASCII
    console.print(Align.center(Panel(
        RICK_ASCII,
        title="[bold yellow]✨ RICK-ROLL PAYLOAD ✨[/bold yellow]",
        border_style="yellow",
        box=box.DOUBLE
    )))

    console.print()

    # Mensaje para salir en la esquina inferior izquierda
    quit_message = Text("Press ", style="italic white") + Text("F", style="bold red") + Text(" to quit", style="italic white")
    quit_panel = Panel(quit_message, border_style="red", width=25)
    console.print(quit_panel)

    # Bucle para esperar la 'f' y salir
    try:
        while True:
            char = getch()
            if char.lower() == 'f':
                break
            # Permitir salir con Ctrl+C también
            if ord(char) == 3:
                break
    except (KeyboardInterrupt, SystemExit):
        # Ignorar y proceder al mensaje final
        pass
    finally:
        console.print(Align.center("\n[bold red]¡Misión cumplida! Volviendo a la base...[/bold red]"))

if __name__ == "__main__":
    run()
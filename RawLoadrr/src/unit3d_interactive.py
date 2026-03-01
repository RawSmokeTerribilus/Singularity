# -*- coding: utf-8 -*-
"""
Interactive Unit3D Tracker Setup Interface

Run with: python3 -m src.unit3d_interactive
or:       python3 src/unit3d_interactive.py

This provides an interactive TUI to:
1. Use existing trackers from config.py
2. Configure new trackers dynamically
3. Manage saved tracker sessions
"""

import sys
import os
import json
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.console import console
from src.unit3d_config import Unit3DTrackerConfig, create_dynamic_tracker_module
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table


class Unit3DInteractiveSetup:
    """Main interactive setup interface"""
    
    def __init__(self):
        self.config_manager = Unit3DTrackerConfig()
        self.selected_tracker = None
    
    def run(self):
        """Main entry point"""
        console.print("\n")
        console.rule("[bold cyan]GENERIC UNIT3D TRACKER SETUP[/bold cyan]")
        
        while True:
            self._show_main_menu()
            choice = Prompt.ask(
                "Select option",
                choices=["1", "2", "3", "4"],
                default="1"
            )
            
            if choice == "1":
                self._use_existing_tracker()
            elif choice == "2":
                self._setup_new_tracker()
            elif choice == "3":
                self._load_saved_session()
            elif choice == "4":
                self._list_sessions()
            
            if self.selected_tracker:
                console.print("\n[bold green]✓ Tracker configured![/bold green]")
                if Confirm.ask("Ready to upload?", default=True):
                    self._show_upload_commands()
                    break
                else:
                    self.selected_tracker = None
    
    def _show_main_menu(self):
        """Display main menu"""
        menu = """
[bold cyan]Options:[/bold cyan]
  [1] Use existing tracker (from config.py)
  [2] Configure new tracker
  [3] Load saved tracker session
  [4] List saved sessions
"""
        console.print(Panel(menu, border_style="cyan"))
    
    def _use_existing_tracker(self):
        """Select from existing trackers in config.py"""
        try:
            from data.config import config
            
            # Filter out non-tracker entries (like 'default_trackers')
            all_keys = config.get('TRACKERS', {}).keys()
            trackers = [t for t in all_keys if isinstance(config['TRACKERS'][t], dict)]
            
            if not trackers:
                console.print("[red]✗ No trackers found in config.py[/red]")
                return
            
            console.print("\n[bold]Available trackers:[/bold]")
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("#", style="dim")
            table.add_column("Tracker")
            table.add_column("API Token", style="dim")
            
            for i, tracker in enumerate(trackers, 1):
                api_key = config['TRACKERS'][tracker].get('api_key', 'N/A')
                display_key = f"{api_key[:15]}..." if len(api_key) > 15 else api_key
                table.add_row(str(i), tracker, display_key)
            
            console.print(table)
            
            choice_str = Prompt.ask(
                "Select tracker",
                default="1"
            )
            try:
                choice = int(choice_str)
            except ValueError:
                choice = 0
            
            if 1 <= choice <= len(trackers):
                tracker_name = trackers[choice - 1]
                tracker_config = config['TRACKERS'][tracker_name]
                
                self.selected_tracker = {
                    'name': tracker_name,
                    'url': tracker_config.get('announce_url', '').split('/announce')[0],
                    'api_key': tracker_config.get('api_key'),
                    'api_token_param': 'api_token',
                    'source': 'config'
                }
                
                console.print(f"\n[green]✓ Selected:[/green] {tracker_name}")
                self.config_manager.save_session(self.selected_tracker)
            else:
                console.print("[red]Invalid choice[/red]")
        
        except ImportError:
            console.print("[red]✗ config.py not found[/red]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    
    def _setup_new_tracker(self):
        """Configure a brand new tracker"""
        config = self.config_manager.interactive_setup()
        if config:
            self.selected_tracker = config
            self.config_manager.save_session(config)
    
    def _load_saved_session(self):
        """Load a previously saved tracker session"""
        sessions = self.config_manager.list_saved_sessions()
        
        if not sessions:
            console.print("[yellow]No saved sessions found[/yellow]")
            return
        
        console.print("\n[bold]Saved sessions:[/bold]")
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim")
        table.add_column("Session File")
        
        for i, session in enumerate(sessions[:10], 1):  # Show last 10
            table.add_row(str(i), session)
        
        console.print(table)
        
        choice_str = Prompt.ask(
            "Select session",
            default="1"
        )
        try:
            choice = int(choice_str)
        except ValueError:
            choice = 0
        
        if 1 <= choice <= len(sessions):
            session_path = os.path.join(
                self.config_manager.sessions_dir,
                sessions[choice - 1]
            )
            self.selected_tracker = self.config_manager.load_session(session_path)
            if self.selected_tracker:
                console.print(f"\n[green]✓ Loaded:[/green] {self.selected_tracker['name']}")
    
    def _list_sessions(self):
        """Show all saved sessions"""
        sessions = self.config_manager.list_saved_sessions()
        
        if not sessions:
            console.print("[yellow]No saved sessions[/yellow]")
            return
        
        console.print(f"\n[bold]Total sessions: {len(sessions)}[/bold]\n")
        
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Session File")
        table.add_column("Size", style="dim")
        
        for session in sessions[:20]:  # Show first 20
            session_path = os.path.join(self.config_manager.sessions_dir, session)
            size = os.path.getsize(session_path)
            table.add_row(session, f"{size} bytes")
        
        console.print(table)
    
    def _show_upload_commands(self):
        """Show how to use the tracker with upload.py"""
        if not self.selected_tracker:
            return
        
        tracker_name = self.selected_tracker['name']
        url = self.selected_tracker['url']
        
        console.print()
        console.print(Panel(f"""
[bold green]Upload Commands:[/bold green]

[bold cyan]Single file:[/bold cyan]
python3 upload.py --tracker {tracker_name} --input /path/to/content.mkv --unattended

[bold cyan]Directory (recursive):[/bold cyan]
python3 upload.py --tracker {tracker_name} --input /path/to/directory --recursive --unattended

[bold cyan]Watch logs:[/bold cyan]
tail -f logs/{tracker_name}_errors.log
tail -f logs/{tracker_name}_debug.log

[bold yellow]Configuration:[/bold yellow]
Tracker: {tracker_name}
URL: {url}
""", border_style="green"))
        
        console.print("\n[yellow]ℹ️ Session saved for quick access next time![/yellow]")


def main():
    """Entry point"""
    try:
        setup = Unit3DInteractiveSetup()
        setup.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Setup cancelled[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

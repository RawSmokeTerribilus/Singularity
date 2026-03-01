#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit3D Interactive TUI - Demo & Testing Guide

This script shows you how to use the interactive TUI in different ways.
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from src.console import console
from src.unit3d_config import Unit3DTrackerConfig
from data.config import config

def show_menu():
    """Display usage options"""
    console.clear()
    
    menu = """
╔════════════════════════════════════════════════════════════════╗
║           GENERIC UNIT3D TRACKER TUI - USAGE GUIDE             ║
║                                                                ║
║    Launch Interactive Setup For Any Unit3D Tracker             ║
╚════════════════════════════════════════════════════════════════╝

[bold cyan]🎯 THREE WAYS TO USE THE TUI:[/bold cyan]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[bold yellow]METHOD 1: Interactive Mode (Recommended)[/bold yellow]

Run the TUI interactively to select or configure trackers:

    [cyan]$ python3 src/unit3d_interactive.py[/cyan]

Then follow the prompts:
  1. Choose an option:
     [1] Use existing tracker (from config.py)
     [2] Configure new tracker
     [3] Load saved tracker session
     [4] List saved sessions

  2. Fill in required information
  3. TUI auto-saves your session
  4. Ready to upload!

[bold cyan]✓ Best for:[/bold cyan] First-time setup, new trackers

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[bold yellow]METHOD 2: Quick Test (Use Existing Tracker)[/bold yellow]

Test with a tracker already in config.py:

    [cyan]$ python3 << 'EOF'
from src.unit3d_config import Unit3DTrackerConfig
from data.config import config

# Get first available tracker
config_mgr = Unit3DTrackerConfig()
trackers = [t for t in config['TRACKERS'].keys() 
           if isinstance(config['TRACKERS'][t], dict)]

tracker = trackers[0] if trackers else 'MILNU'
tracker_cfg = config['TRACKERS'][tracker]

# Create session-ready config
tracked_config = {
    'name': tracker,
    'url': tracker_cfg.get('announce_url', '').split('/announce')[0],
    'api_key': tracker_cfg.get('api_key'),
    'api_token_param': 'api_token',
    'source': 'config'
}

print(f"✓ Loaded: {tracked_config['name']}")
print(f"  URL: {tracked_config['url']}")
print(f"  API Key: {tracked_config['api_key'][:20]}...")
EOF[/cyan]

[bold cyan]✓ Best for:[/bold cyan] Quick verification, existing trackers

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[bold yellow]METHOD 3: Post-Setup Upload[/bold yellow]

After TUI setup, upload immediately with the discovered tracker:

    [cyan]$ python3 src/unit3d_interactive.py[/cyan]
    (Select/configure tracker)
    (TUI shows: "Ready to upload? [Y/n]:")
    Press [cyan]Y[/cyan] to see upload commands

Or manually upload with configured tracker:

    [cyan]$ python3 upload.py --tracker MYTRACKER --input video.mkv --unattended[/cyan]

Session was auto-saved to: [cyan]tmp/tracker_sessions/[/cyan]

[bold cyan]✓ Best for:[/bold cyan] Production uploads, automation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[bold cyan]📋 AVAILABLE TRACKERS (Already in config.py):[/bold cyan]

"""
    console.print(menu)
    
    # List available trackers
    config_mgr = Unit3DTrackerConfig()
    trackers_dict = config.get('TRACKERS', {})
    valid_trackers = sorted([t for t in trackers_dict.keys() 
                            if isinstance(trackers_dict[t], dict)])
    
    console.print("[bright_blue]Valid Trackers (Ready to use):[/bright_blue]")
    
    # Show in columns
    for i, tracker in enumerate(valid_trackers, 1):
        api_key = trackers_dict[tracker].get('api_key', '')
        has_key = "✓" if api_key and api_key != 'N/A' else "✗"
        console.print(f"  {has_key} [{i:2d}] {tracker:15} | API configured")
        if i % 3 == 0 and i < len(valid_trackers):
            pass  # Continue to next line
    
    console.print(f"\n[bold yellow]Total: {len(valid_trackers)} trackers available[/bold yellow]\n")
    
    console.print("""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[bold cyan]🚀 QUICK START:[/bold cyan]

    # 1. Launch TUI
    python3 src/unit3d_interactive.py

    # 2. Select option [1] (use MILNU or EMU)
    # 3. Select tracker from list
    # 4. Get ready-to-use upload command

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[bold green]✨ Session Files Saved:[/bold green]
  Location: [cyan]tmp/tracker_sessions/[/cyan]
  Format: [cyan]session_TRACKER_timestamp.json[/cyan]
  Auto-saved: ✓ Yes

[bold yellow]💡 Tip:[/bold yellow] Sessions are reusable! Load old sessions 
  without re-entering tracker details.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[bold magenta]Ready to test?[/bold magenta] Press [bold cyan]ENTER[/bold cyan] to launch TUI...
""")

def main():
    show_menu()
    input()  # Wait for user
    
    # Launch the actual TUI
    from src.unit3d_interactive import Unit3DInteractiveSetup
    try:
        setup = Unit3DInteractiveSetup()
        setup.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Setup cancelled[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()

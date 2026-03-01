# -*- coding: utf-8 -*-
"""
Generic Unit3D Tracker Configuration Module

Interactive setup for any Unit3D-based tracker without editing config.py
Allows dynamic tracker addition with minimal configuration.
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
from src.console import console
from rich.prompt import Prompt, Confirm


class Unit3DTrackerConfig:
    """
    Dynamic Unit3D tracker configuration handler.
    
    Allows users to upload to any Unit3D-based tracker by providing:
    - Tracker URL
    - API Key
    - Category/Type/Resolution mappings (optional, uses defaults)
    """
    
    def __init__(self, base_dir: str = None):
        """
        Initialize tracker config manager.
        
        Args:
            base_dir: Base directory for saving session configs (default: ./tmp)
        """
        self.base_dir = base_dir or os.path.join(os.getcwd(), 'tmp')
        self.sessions_dir = os.path.join(self.base_dir, 'tracker_sessions')
        Path(self.sessions_dir).mkdir(parents=True, exist_ok=True)
        
        # Default Unit3D category/type/resolution mappings
        self.default_mappings = {
            'categories': {
                'MOVIE': '1',
                'TV': '2',
            },
            'types': {
                'DISC': '1',
                'REMUX': '2',
                'WEBDL': '4',
                'WEBRIP': '5',
                'HDTV': '6',
                'ENCODE': '3'
            },
            'resolutions': {
                '8640p': '10',
                '4320p': '1',
                '2160p': '2',
                '1440p': '3',
                '1080p': '3',
                '1080i': '4',
                '720p': '5',
                '576p': '6',
                '576i': '7',
                '480p': '8',
                '480i': '9'
            }
        }
    
    def interactive_setup(self) -> Optional[Dict]:
        """
        Interactive TUI for setting up a new tracker.
        
        Returns:
            Dict with tracker config or None if cancelled
        """
        console.print("\n" + "="*60)
        console.print("[bold cyan]🎯 GENERIC UNIT3D TRACKER SETUP[/bold cyan]")
        console.print("="*60 + "\n")
        
        # Step 1: Tracker selection
        console.print("[bold]1. Tracker Selection[/bold]")
        console.print("   [1] Use existing tracker from config")
        console.print("   [2] New tracker (provide URL + API key)")
        choice = Prompt.ask("   Select", choices=["1", "2"], default="2")
        
        if choice == "1":
            return self._select_from_config()
        else:
            return self._configure_new_tracker()
    
    def _select_from_config(self) -> Optional[Dict]:
        """Let user select from existing trackers in config.py"""
        try:
            from data.config import config
            
            # Filter out non-tracker entries (like 'default_trackers')
            all_keys = config.get('TRACKERS', {}).keys()
            trackers = [t for t in all_keys if isinstance(config['TRACKERS'][t], dict)]
            
            if not trackers:
                console.print("[red]No trackers found in config.py[/red]")
                return None
            
            console.print("\n[bold]Available trackers:[/bold]")
            for i, tracker in enumerate(trackers, 1):
                console.print(f"   [{i}] {tracker}")
            
            choice_str = Prompt.ask("Select tracker", default="1")
            try:
                choice = int(choice_str)
            except ValueError:
                choice = 0
            if 1 <= choice <= len(trackers):
                tracker_name = trackers[choice - 1]
                tracker_config = config['TRACKERS'][tracker_name]
                
                return {
                    'name': tracker_name,
                    'url': tracker_config.get('announce_url', '').split('/announce')[0],
                    'api_key': tracker_config.get('api_key'),
                    'api_token_param': 'api_token',
                    'source': 'config'
                }
        except Exception as e:
            console.print(f"[red]Error reading config: {e}[/red]")
        
        return None
    
    def _configure_new_tracker(self) -> Dict:
        """Configure a completely new tracker"""
        console.print("\n[bold]2. New Tracker Configuration[/bold]\n")
        
        # Get tracker info
        tracker_name = Prompt.ask("   Tracker name (e.g., MYTRACKER)")
        tracker_name = tracker_name.upper()
        
        tracker_url = Prompt.ask("   Tracker URL (e.g., https://tracker.example.com)")
        if not tracker_url.startswith('http'):
            tracker_url = f"https://{tracker_url}"
        
        api_key = Prompt.ask("   API Key")
        
        api_token_param = Prompt.ask(
            "   API token parameter name",
            default="api_token",
            show_default=True
        )
        
        # Optional: Custom mappings
        use_custom_mappings = Confirm.ask(
            "\n   Use custom category/type/resolution mappings?",
            default=False
        )
        
        config_dict = {
            'name': tracker_name,
            'url': tracker_url,
            'api_key': api_key,
            'api_token_param': api_token_param,
            'source': 'dynamic'
        }
        
        if use_custom_mappings:
            config_dict['mappings'] = self._get_custom_mappings()
        else:
            config_dict['mappings'] = self.default_mappings
        
        # Summarize
        console.print("\n[bold green]✓ Configuration Summary:[/bold green]")
        console.print(f"   Name: {config_dict['name']}")
        console.print(f"   URL: {config_dict['url']}")
        console.print(f"   API Key: {config_dict['api_key'][:20]}...")
        console.print(f"   API Param: {config_dict['api_token_param']}")
        
        if Confirm.ask("\n   Valid?", default=True):
            return config_dict
        else:
            console.print("[yellow]Setup cancelled[/yellow]")
            return None
    
    def _get_custom_mappings(self) -> Dict:
        """Get custom category/type/resolution mappings from user"""
        console.print("\n   [bold]Custom Mappings (or press Enter to skip category)[/bold]")
        
        mappings = {
            'categories': {},
            'types': {},
            'resolutions': {}
        }
        
        # Categories
        console.print("\n   [bold]Categories:[/bold]")
        while True:
            cat_name = Prompt.ask("      Category name (e.g., MOVIE)", default="").upper()
            if not cat_name:
                break
            cat_id = Prompt.ask(f"         ID for {cat_name}")
            mappings['categories'][cat_name] = cat_id
        
        # Types
        console.print("\n   [bold]Types:[/bold]")
        while True:
            type_name = Prompt.ask("      Type name (e.g., REMUX)", default="").upper()
            if not type_name:
                break
            type_id = Prompt.ask(f"         ID for {type_name}")
            mappings['types'][type_name] = type_id
        
        # Resolutions
        console.print("\n   [bold]Resolutions:[/bold]")
        while True:
            res_name = Prompt.ask("      Resolution name (e.g., 1080p)", default="")
            if not res_name:
                break
            res_id = Prompt.ask(f"         ID for {res_name}")
            mappings['resolutions'][res_name] = res_id
        
        return mappings
    
    def save_session(self, tracker_config: Dict) -> str:
        """
        Save tracker config as a session file.
        
        Args:
            tracker_config: Dict with tracker configuration
            
        Returns:
            Path to saved session file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        session_name = f"session_{tracker_config['name']}_{timestamp}.json"
        session_path = os.path.join(self.sessions_dir, session_name)
        
        with open(session_path, 'w') as f:
            json.dump(tracker_config, f, indent=2)
        
        console.print(f"\n[green]✓ Session saved:[/green] {session_path}")
        return session_path
    
    def load_session(self, session_path: str) -> Optional[Dict]:
        """
        Load a previously saved tracker session.
        
        Args:
            session_path: Path to session JSON file
            
        Returns:
            Tracker config dict or None if not found
        """
        if not os.path.exists(session_path):
            console.print(f"[red]Session not found: {session_path}[/red]")
            return None
        
        try:
            with open(session_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            console.print(f"[red]Error loading session: {e}[/red]")
            return None
    
    def list_saved_sessions(self) -> list:
        """List all saved tracker sessions"""
        sessions = []
        if os.path.exists(self.sessions_dir):
            sessions = [f for f in os.listdir(self.sessions_dir) if f.endswith('.json')]
        return sorted(sessions, reverse=True)


def create_dynamic_tracker_module(tracker_config: Dict) -> str:
    """
    Create a dynamic tracker module from configuration.
    
    Args:
        tracker_config: Dict with tracker configuration
        
    Returns:
        Module name (tracker identifier)
    """
    tracker_name = tracker_config['name']
    api_key = tracker_config['api_key']
    tracker_url = tracker_config['url']
    api_token_param = tracker_config.get('api_token_param', 'api_token')
    mappings = tracker_config.get('mappings', {
        'categories': {'MOVIE': '1', 'TV': '2'},
        'types': {'DISC': '1', 'REMUX': '2', 'WEBDL': '4', 'WEBRIP': '5', 'HDTV': '6', 'ENCODE': '3'},
        'resolutions': {'1080p': '3', '720p': '5', '2160p': '2'}
    })
    
    # Create dynamic config in memory (would need to be integrated with upload.py)
    dynamic_config = {
        tracker_name: {
            'api_key': api_key,
            'announce_url': f"{tracker_url}/announce/Custom_Announce_URL",
            'anon': False,
            'mappings': mappings,
            'source_flag': tracker_name.lower()
        }
    }
    
    return tracker_name, dynamic_config

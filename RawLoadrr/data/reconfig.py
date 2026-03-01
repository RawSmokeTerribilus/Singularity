import os
import re
import copy
import operator
import pprint
import argparse
from rich import print as Print
from rich.console import Console
from rich.prompt import Prompt
from packaging import version

console = Console()

class DoubleQuoteDict(dict):
    def __str__(self):
        parts = []
        for k, v in self.items():
            if isinstance(v, str):
                v = '"' + v.replace('\n', '\\n') + '"'
            parts.append(f"\"{k}\": {v}")
        return "{" + ", ".join(parts) + "}"

class CustomPrettyPrinter(pprint.PrettyPrinter):
    def _format(self, object, stream, indent, allowance, context, level):
        if isinstance(object, dict):
            stream.write("{\n")
            self._indent_per_level += 1
            for i, (key, value) in enumerate(object.items()):
                if level == 1:
                    stream.write("    ")
                if level == 2:
                    stream.write("            ")
                if isinstance(value, dict):
                    stream.write("\"{}\": ".format(key))
                    self._format(value, stream, indent, allowance + 1, context, level + 1)
                else:
                    if isinstance(value, str):
                        value = value.replace('\n', '\\n')
                        value = f'"{value}"'
                    stream.write("\"{}\": {}".format(key, value))
                if i < len(object) - 1:
                    stream.write(",")
                    if level == 0 or (level == 1 and isinstance(value, dict)):
                        stream.write("\n\n")
                    else:
                        stream.write("\n")
            self._indent_per_level -= 1
            stream.write("\n}")
        else:
            super()._format(object, stream, indent, allowance, context, level)

def read_config(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        exec(file.read())
    return locals()['config']

def write_config(file_path, config_dict):
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(f"\n        ##---------THE LAST DIGITAL UNDERGROUND PRESENTS-------##\n        ##                                                     ##\n        ##                 Special Recruitment :)              ##\n        ##          @ https://TheLDU.to/application            ##\n        ##                                                     ##\n        ##                              Ref: Uploadrr by CvT   ##\n        ##-----------------------------------------------------##\n\n  #Refer to `/backup/example-config.py` for additional options + comments\n\n")
        file.write('config = ')
        printer = CustomPrettyPrinter(stream=file)
        printer.pprint(config_dict)

def replace_values(base_dict, old_dict):
    special_cases = {
        'global_sig': '\n[center][size=6][url=https://github.com/z-ink/Upload-Assistant]Upload Assistant(CvT Mod v0.4)[/url][/size][/center]',
        'global_anon_sig': '\n[center][size=6]we are anonymous[/size][/center]',
        'anon_signature': '\n[center][size=6]we are anonymous[/size][/center]'
    }

    def replace_urls(value):
        if isinstance(value, str):
            value = value.replace("https://github.com/z-ink/Upload-Assistant", "https://codeberg.org/CvT/Uploadrr")
            value = value.replace("https://github.com/z-ink/Uploadrr", "https://codeberg.org/CvT/Uploadrr")
            value = value.replace("https://github.com/z-ink/uploadrr", "https://codeberg.org/CvT/Uploadrr")
        return value

    for key, old_value in old_dict.items():
        if key in base_dict:
            if key == 'version':
                continue
            if isinstance(old_value, dict):
                replace_values(base_dict[key], old_value)  # Recurse into nested dictionaries
            else:
                # Handle special cases
                if key in special_cases and old_value == special_cases[key]:
                    continue

                # Handle signature replacement
                if key == 'signature':
                    if key in special_cases:
                        base_dict[key] = special_cases[key]
                    else:
                        match = re.search(r'PLEASE SEED (.*) FAMILY', old_value)
                        if match:
                            continue
                        elif "[size=6][url=https://github.com/z-ink/Upload-Assistant]Upload Assistant(CvT Mod v0.4)[/url][/size]" in old_value:
                            base_dict[key] = old_value.replace(
                                "[size=6][url=https://github.com/z-ink/Upload-Assistant]Upload Assistant(CvT Mod v0.4)[/url][/size]", 
                                "[url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url]"
                            )
                        elif "[size=6][url=https://github.com/z-ink/Upload-Assistant]Upload Assistant(CvT Mod v0.3)[/url][/size]" in old_value:
                            base_dict[key] = old_value.replace(
                                "[size=6][url=https://github.com/z-ink/Upload-Assistant]Upload Assistant(CvT Mod v0.3)[/url][/size]", 
                                "[url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url]"
                            )
                        elif "[url=https://github.com/z-ink/Uploadrr]" in old_value:
                            base_dict[key] = old_value.replace("https://github.com/z-ink/Uploadrr", "https://codeberg.org/CvT/Uploadrr")
                        elif "[url=https://github.com/z-ink/uploadrr]" in old_value:
                            base_dict[key] = old_value.replace("https://github.com/z-ink/uploadrr", "https://codeberg.org/CvT/Uploadrr")
                        else:
                            base_dict[key] = old_value
                else:
                    # Apply URL replacements globally to other values
                    base_dict[key] = replace_urls(old_value)
        else:
            # Apply URL replacements globally if the key doesn't exist in base_dict
            base_dict[key] = replace_urls(old_value)

parser = argparse.ArgumentParser(description='Reconfigure the config file.')
parser.add_argument('--output-dir', type=str, required=True, help='The directory where the new config.py should be written.')
args = parser.parse_args()
output_dir = args.output_dir

data_dir = os.path.dirname(os.path.realpath(__file__))
backup_dir = os.path.join(data_dir, 'backup')

def reconfigure():
    base_config_path = os.path.join(backup_dir, 'example_config.py')
    old_config_path = os.path.join(backup_dir, 'old_config.py')
    new_config_path = os.path.join(output_dir, 'config.py')
    
    try:
        base_config = read_config(base_config_path)
        old_config = read_config(old_config_path)
    except Exception as e:
        console.print(f"[bold red]ERROR[/bold red]: {e}")
        return

    new_config = copy.deepcopy(base_config)
    replace_values(new_config, old_config)

    if os.path.exists(new_config_path):
        current_config = read_config(new_config_path)
    else:
        current_config = {'version': '0'}

    if not os.path.exists(old_config_path):
        console.print("[bold red]WARN[/bold red]: [bold]old_config.py[/bold] not found, please rename your old `config.py` to `old_config.py` and try again")
        return

    if os.path.exists(new_config_path):
        if version.parse(current_config.get('version', '0')) > version.parse(base_config.get('version', '0')):
            console.print("[bold red]WARN[/bold red]: The current config file has a higher version number than the example config file.")
            console.print("[bold red]WARN[/bold red]: Continuing will [bold]downgrade[/bold] the configuration file and may cause [bold]incompatibility issues[/bold].")
            overwrite = Prompt.ask("Do you wish to continue?", choices=["y", "N"], default="N")
            if overwrite.lower() != 'y':
                return
        else:
            overwrite = Prompt.ask("[bold red]WARN[/bold red]: [bold]config.py[/bold] exists, if you continue you will [bold]OVERWRITE[/bold] your current config, do you wish to continue?", choices=["y", "N"], default="N")
            if overwrite.lower() != 'y':
                return

    # Add additional TRACKERS
    added_blocks = []
    for key in old_config['TRACKERS']:
        if key not in new_config['TRACKERS']:
            new_config['TRACKERS'][key] = old_config['TRACKERS'][key]
            added_blocks.append(key)
    
    default_value = new_config['TRACKERS'].pop('default_trackers', None)
    
    # Sort TRACKERS alphabetically
    new_config['TRACKERS'] = dict(sorted(new_config['TRACKERS'].items(), key=operator.itemgetter(0)))
    
    if default_value is not None:
        new_config['TRACKERS'] = {'default_trackers': default_value, **new_config['TRACKERS']}

    try:
        write_config(new_config_path, new_config)
    except Exception as e:
        console.print(f"[bold red]ERROR[/bold red]: {e}")
        return

    Print('[bold green]Congratulations! config.py was successfully updated.[/bold green]')
    Print('[bold yellow]WARN[/bold yellow]: It is recommended you double check your client settings.')
    if added_blocks:
        Print('[bold yellow]WARN[/bold yellow]: The following [i]not built-in[/i] TRACKERS: [bold]' + '[/bold], [bold]'.join(added_blocks) + '[/bold] were added.') 
        Print('[bold yellow]WARN[/bold yellow]: Please be sure to add them in `upload.py` and add the .py files into `/src/trackers`')
        Print('[bold red]WARN[/bold yellow]: Note that you should recreate the Tracker using the template as changes have been made, and script will break if left alone.')

reconfigure()
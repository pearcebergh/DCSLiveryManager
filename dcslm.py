from requests import get
from rich.progress import track
from rich.console import Console
from rich.rule import Rule
from datetime import datetime
import os
import platform
from DCSLM import __version__
from prompt_toolkit import PromptSession, HTML
from prompt_toolkit.shortcuts import confirm
from prompt_toolkit.completion import WordCompleter, NestedCompleter

if platform.system() == 'Windows':
    from ctypes import windll, wintypes

def set_terminal_title(title):
    if platform.system() == 'Windows':
        os.system(f'title {title}')
    else:
        os.system(f'echo "\033]0;{title}\007"')


def clear():
    if platform.system() == 'Windows':
        os.system('cls')
    else:
        os.system('clear')


def set_terminal_size(w, h):
    if platform.system() == 'Windows':
        os.system(f'mode con: cols={w} lines={h}')
    else:
        os.system(f'printf \'\033[8;{h};{w}t\'')


class DCSLM:
    def __init__(self):
        self.headless = False
        self.console = None
        self.session = PromptSession(reserve_space_for_menu=6, complete_in_thread=True)
        self.completer = None
        self.commands = None

    def start(self):
        self.setup_commands()
        self.setup_command_completer()
        self.setup_console_window()
        self.clear_and_print_header()
        self.print_help()
        self.run()


    def setup_commands(self):
        self.commands = {
            'install': {
                'completer': None,
                'usage': "\[id/url1] \[id/url2] \[id/url3] ...",
                'desc': "Install DCS liveries from DCS User Files URLs or IDs",
                'flags': {},
                'exec': None
            },
            'uninstall': {
                'completer': None,
                'usage': "\[id1] \[id2] \[id3] ...",
                'desc': "Uninstall DCS liveries that are currently installed from their ID",
                'flags': {
                    'all': {
                        'tags': ['-a', '--all'],
                        'desc': "Uninstalls all tracked liveries",
                        'confirm': True
                    },
                    'keep': {
                        'tags': ['-k', '--keep'],
                        'desc': "Keep livery files on disk (untrack them)",
                        'confirm': False
                    }
                },
                'exec': None
            },
            'list': {
                'completer': None,
                'usage': "",
                'desc': "List currently installed DCS liveries",
                'flags': {},
                'exec': None
            },
            'check': {
                'completer': None,
                'usage': "",
                'desc': "Check for updates to any installed liveries",
                'flags': {},
                'exec': None
            },
            'scan': {
                'completer': None,
                'usage': "",
                'desc': "Scan DCS liveries folder for installed liveries",
                'flags': {},
                'exec': None
            },
            'help': {
                'completer': None,
                'usage': "",
                'desc': "List the commands and their usage",
                'flags': {},
                'exec': self.print_help
            },
            'exit': {
                'completer': None,
                'usage': "",
                'desc': "Exit the DCS Livery Manager program",
                'flags': {},
                'exec': None
            }
        }


    def print_help(self):
        for k, v in self.commands.items():
            self.console.print("[deep_pink2]" + k + "[/deep_pink2] [sky_blue1]" + v['usage'] + "[/sky_blue1]")
            self.console.print("\t" + v['desc'])
            if len(v['flags']):
                self.console.print("\t[bold]Flags:[/bold]")
                for j, k in v['flags'].items():
                    self.console.print("\t\t[bold]" + ', '.join(k['tags']) + "[/bold] - " + k['desc'])

        self.console.print("\n")


    def setup_command_completer(self):
        completerDict = {}
        for k,v in self.commands.items():
            completerDict[k] = v['completer']
        self.completer = NestedCompleter.from_nested_dict(completerDict)

    def clear_and_print_header(self):
        clear()
        self.console.print(Rule(f'[bold gold1]DCS Livery Manager[/bold gold1] [bold sky_blue1]v{__version__}[/bold sky_blue1]', characters="~═~*", style="deep_pink2"))
        self.console.print('')


    def setup_console_window(self):
        self.console = Console()
        set_terminal_size(120,40)


    def run(self):
        runCommands = True
        while runCommands:
            try:
                command = self.session.prompt(HTML('<ansibrightcyan>DCSLM></ansibrightcyan> '), completer=self.completer)
            except KeyboardInterrupt:
                continue
            except EOFError:
                break
            else:
                splitCommand = command.split(' ', 1)
                if len(splitCommand):
                    if splitCommand[0] in self.commands:
                        self.console.print("Running Command \'" + splitCommand[0] + "\'")
                        commandData = self.commands[splitCommand[0]]
                        if commandData['exec']:
                            commandData['exec']()
                        if splitCommand[0] == "exit":
                            runCommands = False
                    else:
                        self.console.print("Command \'" + splitCommand[0] + "\' not found.")
                else:
                    self.console.print("Command \'" + command + "\' not found.")


if __name__ == '__main__':
    print(platform.system())
    set_terminal_title(f'DCS Livery Manager v{__version__}')
    app = DCSLM()
    app.start()

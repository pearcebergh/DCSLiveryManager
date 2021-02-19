from requests import get
from rich.progress import track
from rich.console import Console
from rich.rule import Rule
from datetime import datetime
import os
import sys
import platform
from DCSLM import __version__
from prompt_toolkit import PromptSession, HTML
from prompt_toolkit.shortcuts import confirm
from prompt_toolkit.completion import WordCompleter, NestedCompleter
from DCSLM import  UnitConfig, Utilities
from DCSLM.Livery import DCSUserFile, Livery
from DCSLM.LiveryManager import LiveryManager

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


class DCSLMApp:
  def __init__(self):
    self.headless = False
    self.console = None
    self.session = PromptSession(reserve_space_for_menu=6, complete_in_thread=True)
    self.completer = None
    self.commands = None
    self.lm = None

  def start(self):
    self.setup_commands()
    self.setup_command_completer()
    self.setup_console_window()
    self.clear_and_print_header()
    self.setup_livery_manager()
    #self.print_help()
    self.run()

  def setup_commands(self):
    self.commands = {
      'install': {
        'completer': None,
        'usage': "\[id/url1] \[id/url2] \[id/url3] ...",
        'desc': "Install DCS liveries from DCS User Files URLs or IDs",
        'flags': {},
        'args': {
          'id/url': {
            'type': "number/string",
            'optional': False,
            'desc': "DCS User Files ID or URL"
          },
        },
        'exec': self.install_liveries
      },
      'uninstall': {
        'completer': None,
        'usage': "\[flags] livery",
        'desc': "Uninstall the given managed livery",
        'flags': {
          'keep': {
            'tags': ['-k', '--keep'],
            'desc': "Keep livery files on disk (untrack them)",
            'confirm': False
          }
        },
        'args': {
          'livery': {
            'type': "string",
            'optional': False,
            'desc': "DCS User Files livery title"
          },
        },
        'exec': None
      },
      'list': {
        'completer': None,
        'usage': "",
        'desc': "List currently installed DCS liveries",
        'flags': {},
        'args': {},
        'exec': None
      },
      'check': {
        'completer': None,
        'usage': "",
        'desc': "Check for updates to any installed liveries",
        'flags': {},
        'args': {},
        'exec': None
      },
      'info': {
        'completer': None,
        'usage': "livery",
        'desc': "Get additional info about an installed livery",
        'flags': {},
        'args': {
          'livery': {
            'type': "string",
            'optional': False,
            'desc': "DCS User Files livery title"
          },
        },
        'exec': None
      },
      'scan': {
        'completer': None,
        'usage': "",
        'desc': "Scan DCS liveries folder for installed liveries",
        'flags': {},
        'args': {},
        'exec': None
      },
      'help': {
        'completer': None,
        'usage': "",
        'desc': "List the commands and their usage",
        'flags': {},
        'args': {},
        'exec': self.print_help
      },
      'exit': {
        'completer': None,
        'usage': "",
        'desc': "Exit the DCS Livery Manager program",
        'flags': {},
        'args': {},
        'exec': None
      },
      'test': {
        'completer': None,
        'usage': "",
        'desc': "This is a test",
        'flags': {},
        'args': {
          'text': {
            'type': "string",
            'optional': False,
            'desc': "A string of text"
          },
        },
        'exec': self.func_test
      }
    }

  def install_liveries(self, sArgs):
    self.console.print("Attempting to download and install " + str(len(sArgs)) + (" liveries." if len(sArgs) > 1 else " livery."))
    for liveryStr in sArgs:
      self.console.print("Attempting to download and install " + liveryStr)
      correctedLiveryStr = Utilities.correct_dcs_user_files_url(liveryStr)
      if correctedLiveryStr:
        livery = Livery()
        #livery.dcsuf = DCSUserFile()
        #livery.dcsuf.id = livery.dcsuf.get_id_from_url(correctedLiveryStr)
        livery._fill_data_test()
        self.print_livery(livery)
        downloadPath = self.lm.download_livery_archive(livery)
        if downloadPath:
          extractPath = self.lm.extract_livery_archive(livery)
          if extractPath:
            detectedLiveries = self.lm.detect_extracted_liveries(livery, extractPath)
            if len(detectedLiveries):
              if self.lm.move_detected_liveries(livery, extractPath, detectedLiveries):
                self.lm.register_livery(livery)
                self.lm.write_livery_registry_file(livery)
            self.lm.remove_extracted_livery_archive(livery, extractPath)
          self.lm.remove_downloaded_archive(livery, downloadPath)

  def func_test(self, sArgs):
    self.console.print(sArgs)

  def print_help(self):
    for k, v in self.commands.items():
      self.console.print("[deep_pink2]" + k + "[/deep_pink2] [sky_blue1]" + v['usage'] + "[/sky_blue1]")
      self.console.print("\t" + v['desc'])
      if len(v['args']):
        self.console.print("\t[bold]Arguments:[/bold]")
        hasOptional = False
        for j, k in v['args'].items():
          if not k['optional']:
            self.console.print("\t\t[bold]" + j + "[/bold] (" + k['type'] + ") - " + k['desc'])
          else:
            hasOptional = True
        if hasOptional:
          self.console.print("\t[bold]Optional Arguments:[/bold]")
          for j, k in v['args'].items():
            if k['optional']:
              self.console.print("\t\t[bold]" + j + "[/bold] (" + k['type'] + ") - " + k['desc'])
      if len(v['flags']):
        self.console.print("\t[bold]Flags:[/bold]")
        for j, k in v['flags'].items():
          self.console.print("\t\t[bold]" + ', '.join(k['tags']) + "[/bold] - " + k['desc'])

    self.console.print("\n")

  def print_livery(self, livery):
    if livery:
      self.console.print(livery.unit + " - \'" + livery.dcsuf.title + "\' by " + livery.dcsuf.author)
      self.console.print("User Files ID: " + str(livery.dcsuf.id) + " \tUpload Date: " + livery.dcsuf.date + " \tDownload Size: " + livery.dcsuf.size)
      self.console.print(livery.archive)

  def setup_command_completer(self):
    completerDict = {}
    for k, v in self.commands.items():
      completerDict[k] = v['completer']
    self.completer = NestedCompleter.from_nested_dict(completerDict)

  def clear_and_print_header(self):
    clear()
    self.console.print(
      Rule(f'[bold gold1]DCS Livery Manager[/bold gold1] [bold sky_blue1]v{__version__}[/bold sky_blue1]',
           characters="~═~*", style="deep_pink2"))
    self.console.print('')

  def setup_console_window(self):
    self.console = Console(width=120)
    #set_terminal_size(80, 50)

  def setup_livery_manager(self):
    self.lm = LiveryManager()
    lmData = self.lm.load_data()
    if not lmData:
      self.console.print("No existing dcslm.json file found with config and livery data. Loading defaults.")
      self.lm.prompt_default_data()
    else:
      self.console.print("Loaded Livery Manager config and data from dcslm.json")
      self.lm = lmData

  def run(self):
    self.console.print("")
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
            argList = []
            if len(splitCommand) == 2:
              argList = str.split(splitCommand[1], ' ')
            if commandData['exec']:
              if len(commandData['args']):
                commandData['exec'](sArgs=argList)
              else:
                commandData['exec']()
            if splitCommand[0] == "exit":
              runCommands = False
          else:
            self.console.print("Command \'" + splitCommand[0] + "\' not found.")
        else:
          self.console.print("Command \'" + command + "\' not found.")
    self.console.print("Writing out current config and livery data to dcslm.json")
    self.lm.write_data()
    self.console.print("Exiting DCS Livery Manager.")


if __name__ == '__main__':
  os.chdir(os.path.dirname(os.path.abspath(sys.executable)))
  set_terminal_title(f'DCS Livery Manager v{__version__}')
  dcslmapp = DCSLMApp()
  dcslmapp.start()

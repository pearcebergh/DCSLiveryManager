from requests import get
from rich.progress import track
from rich.console import Console
from rich.rule import Rule
from rich.prompt import Prompt
from rich.panel import Panel, Padding, PaddingDimensions
from datetime import datetime
import os
import sys
import platform
from DCSLM import __version__
from prompt_toolkit import PromptSession, HTML
from prompt_toolkit.shortcuts import confirm
from prompt_toolkit.completion import WordCompleter, NestedCompleter
from DCSLM import Utilities
from DCSLM.Livery import DCSUserFile, Livery
from DCSLM.LiveryManager import LiveryManager, DCSLMFolderName
from DCSLM.UnitConfig import Units

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
    self.console.print("Installing " + str(len(sArgs)) + (" liveries" if len(sArgs) > 1 else " livery") + " from DCS User Files.")
    for liveryStr in sArgs:
      self.console.print("Attempting to download and install livery from https://www.digitalcombatsimulator.com/en/files/" + liveryStr)
      correctedLiveryStr = Utilities.correct_dcs_user_files_url(liveryStr)
      if correctedLiveryStr:
        #try:
        livery = Livery()
        #livery.dcsuf.id = livery.dcsuf.get_id_from_url(correctedLiveryStr)
        livery._fill_data_test()
        self.print_livery(livery)
        downloadPath = self.lm.download_livery_archive(livery)
        if downloadPath:
          self.console.print(downloadPath)
          extractPath = self.lm.extract_livery_archive(livery)
          if extractPath:
            destinationPath = self.lm.generate_livery_destination_path(livery)
            livery.destination = destinationPath
            unitLiveries = Units.Units['aircraft'][livery.unit]['liveries']
            if len(unitLiveries) > 1:
              unitLiveries = self.prompt_aircraft_livery_choice(livery, unitLiveries)
            self.console.print(unitLiveries)
            installRoots = self.lm.generate_aircraft_livery_install_path(livery, unitLiveries)
            self.console.print(installRoots)
            extractedLiveryFiles = self.lm.get_extracted_livery_files(livery, extractPath)
            self.console.print(extractedLiveryFiles)
            detectedLiveries = self.lm.detect_extracted_liveries(livery, extractedLiveryFiles)
            self.console.print(detectedLiveries)
            if len(detectedLiveries) and len(installRoots):
              installPaths = self.lm.generate_livery_install_paths(installRoots, detectedLiveries)
              self.console.print(installPaths)
              copiedLiveries = self.lm.copy_detected_liveries(livery, extractPath, extractedLiveryFiles, detectedLiveries, installPaths)
              if len(copiedLiveries):
                self.console.print(copiedLiveries)
                livery.install = copiedLiveries
                #self.lm.write_livery_registry_files(livery)
                #self.lm.register_livery(livery)
            self.lm.remove_extracted_livery_archive(livery, extractPath)
          self.lm.remove_downloaded_archive(livery, downloadPath)
        #except Exception as e:
          #self.console.print(e)

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
      self.console.print(Panel("ID: " + str(livery.dcsuf.id) + " | Author: " + livery.dcsuf.author + " | Upload Date: " + livery.dcsuf.date + " | Archive Size: " + livery.dcsuf.size + " \n" + livery.dcsuf.download,
                               title=Units.Units['aircraft'][livery.unit]['friendly'] + " - " + livery.dcsuf.title,
                               expand=False, highlight=True))

  def setup_command_completer(self):
    completerDict = {}
    for k, v in self.commands.items():
      completerDict[k] = v['completer']
    self.completer = NestedCompleter.from_nested_dict(completerDict)

  def clear_and_print_header(self):
    clear()
    self.console.print(Rule(f'[bold gold1]DCS Livery Manager[/bold gold1] [bold sky_blue1]v{__version__}[/bold sky_blue1]',
           characters="~═~*", style="deep_pink2"))
    self.console.print('')

  def setup_console_window(self):
    self.console = Console(width=120)
    #set_terminal_size(80, 50)

  def setup_livery_manager(self):
    self.lm = LiveryManager()
    lmData = self.lm.load_data()
    self.lm.make_dcslm_dirs()
    if not lmData:
      self.console.print("No existing dcslm.json file found with config and livery data. Loading defaults.")
      self.prompt_livery_manager_defaults()
    else:
      self.console.print("Loaded Livery Manager config and data from dcslm.json")
      self.lm.LiveryData = lmData

  def prompt_livery_manager_defaults(self):
    if self.lm:
      self.console.print("\n\n[bold green underline]OVGME (Mod Manager) Mode:")
      self.console.print("If you use a mod manager, like OVGME, to manage your DCS mod installs, you can enable \'OVGME Mode\' to have it create a root directory named with the aircraft and title of the livery.")
      self.console.print("\n[gold1]Make sure you've placed DCSLM inside your mod manager's directory that is configured for the [/gold1]\'DCS Saved Games\'[gold1] directory, not the DCS install directory.[/gold1]")
      ovgme = Prompt.ask("\n[bold]Do you want to enable OVGME (Mod Manager) Mode?[/bold]", choices=["Yes", "No"])
      ovgme = (True if ovgme == "Yes" else False)
      self.lm.LiveryData['config']['ovgme'] = ovgme
      if ovgme:
        self.console.print("[green]Enabling OVGME (Mod Manager) mode.")

  def prompt_aircraft_livery_choice(self, livery, unitLiveries):
    choosenLiveries = []
    liveryChoices = ["All"]
    for u in unitLiveries:
      if u in Units.Units['aircraft'].keys():
        liveryChoices.append(Units.Units['aircraft'][u]['friendly'])
      else:
        liveryChoices.append(u)
    if len(liveryChoices) > 2:
      choiceText = ""
      for i in range(0, len(liveryChoices)):
        choiceText += "[" + str(i) + "]" + liveryChoices[i] + " "
      self.console.print("\nThere are multiple livery install locations for the [bold magenta]" + Units.Units['aircraft'][livery.unit]['friendly'] + "[/bold magenta]. Please choose from one of the following choices by inputting the corresponding index number:")
      self.console.print("\n\t" + choiceText)
      choice = Prompt.ask("\n[bold]Which aircraft do you want the livery to be installed to?[/bold]", choices=[str(i) for i in range(0,len(liveryChoices))])
      if choice == "0":
        choosenLiveries = unitLiveries
      else:
        choosenLiveries = [unitLiveries[int(choice) - 1]]
    return choosenLiveries

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
  #os.chdir(os.path.dirname(os.path.abspath(sys.executable)))
  os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))
  set_terminal_title(f'DCS Livery Manager v{__version__}')
  dcslmapp = DCSLMApp()
  dcslmapp.start()
from rich.console import Console
from rich.rule import Rule
from rich.prompt import Prompt
from rich.panel import Panel, Padding, PaddingDimensions
from rich.table import Table
from rich.live import Live
from rich import box
from rich.align import Align
import argparse
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
from DCSLM.DCSUFParser import DCSUFParser
from rich.progress import (
    BarColumn,
    DownloadColumn,
    TextColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
    Progress,
    TaskID,
)

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
        'flags': {
          'keep': {
            'tags': ['-k', '--keep'],
            'desc': "Keep downloaded livery archive files",
            'confirm': False
          }
        },
        'args': {
          'url': {
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
        'exec': self.list_liveries
      },
      'check': {
        'completer': None,
        'usage': "",
        'desc': "Check for updates to any installed liveries",
        'flags': {},
        'args': {},
        'exec': self.check_liveries
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

  def _parse_install_args(self, sArgs):
      installArgsParser = argparse.ArgumentParser(usage=self.commands['install']['usage'],
                                                  description=self.commands['install']['desc'],
                                                  exit_on_error=False)
      installArgsParser.add_argument(*self.commands['install']['flags']['keep']['tags'], action="store_true",
                                     help=self.commands['install']['flags']['keep']['desc'], dest='keep')
      installArgsParser.add_argument('url', type=str, help=self.commands['install']['args']['url']['desc'], nargs="+")
      parsedArgs = installArgsParser.parse_known_args(sArgs)
      if len(parsedArgs[1]):
        self.console.print("Failed to parse the following args for \'install\':", style="bold red")
        self.console.print("\t" + str(parsedArgs[1]), style="bold red")
      return parsedArgs[0]

  def install_liveries(self, sArgs):
    installArgs = self._parse_install_args(sArgs)
    self.console.print("Attempting to install " + str(len(installArgs.url)) + (" liveries" if len(installArgs.url) > 1 else " livery") + " from DCS User Files.")
    installData = {'success': [], 'failed' : []}
    # TODO: Check for duplicate url/IDs in list
    for liveryStr in installArgs.url:
      correctedLiveryURL = Utilities.correct_dcs_user_files_url(liveryStr)
      if not correctedLiveryURL:
        errorMsg = "Failed to get DCS User Files url or ID from \'" + liveryStr + "\'."
        installData['failed'].append({'url': liveryStr, 'error':errorMsg})
        self.console.print(errorMsg, style="bold red")
      else:
        livery = None
        try:
          with self.console.status("Getting User File information from " + correctedLiveryURL + "..."): livery = self.lm.get_livery_data_from_dcsuf_url(correctedLiveryURL)
          self.console.print("")
          self.print_dcsuf(livery)
          unitLiveries = Units.Units['aircraft'][livery.dcsuf.unit]['liveries']
          if len(unitLiveries) > 1:
            unitLiveries = self.prompt_aircraft_livery_choice(livery, unitLiveries)
          archivePath = self.lm.does_archive_exist(livery.dcsuf.download.split('/')[-1])
          if archivePath:
            self.console.print("Archive file \'" + livery.dcsuf.download.split('/')[-1] + "\' for \'" + livery.dcsuf.title + "\' already exists. Using that instead.")
          else:
            self.console.print("\nDownloading livery archive file " + livery.dcsuf.download)
            archivePath = self._download_archive_progress(livery)
          if archivePath:
            livery.archive = archivePath
            self.console.print("\n[bold]Running extraction program on downloaded archive:")
            extractPath = self.lm.extract_livery_archive(livery)
            if extractPath:
              self.console.print("\nExtracted \'" + livery.archive + "\' to temporary directory.")
              destinationPath = self.lm.generate_livery_destination_path(livery)
              livery.destination = destinationPath
              self.console.print("Detecting extracted liveries...")
              installRoots = self.lm.generate_aircraft_livery_install_path(livery, unitLiveries)
              extractedLiveryFiles = self.lm.get_extracted_livery_files(livery, extractPath)
              detectedLiveries = self.lm.detect_extracted_liveries(livery, extractPath, extractedLiveryFiles)
              if len(detectedLiveries) and len(installRoots):
                self.console.print(detectedLiveries)
                self.console.print("Generating livery install paths...")
                installPaths = self.lm.generate_livery_install_paths(livery, installRoots, detectedLiveries)
                if len(installPaths):
                  self.console.print("Installing " + str(len(detectedLiveries)) + (" liveries" if len(detectedLiveries) > 1 else " livery") + " to " + str(len(installRoots)) + " aircraft.")
                  with self.console.status("Installing extracted liveries..."):copiedLiveries = self.lm.copy_detected_liveries(livery, extractPath, extractedLiveryFiles, installPaths)
                  if len(copiedLiveries):
                    with self.console.status("Writing registry files..."): self.lm.write_livery_registry_files(livery)
                    self.console.print("Wrote " + str(len(installRoots) * len(detectedLiveries)) + " registry files to installed livery directories.")
                    self.lm.register_livery(livery)
                    self.console.print("[bold green]Livery[/bold green] \'" + str(livery.dcsuf.title) + "\' [bold green]Registered!")
                    installData['success'].append(livery)
                  else:
                    raise RuntimeError("Failed to copy livery files to install directories!")
                else:
                  raise RuntimeError("Failed to generate install paths!")
              else:
                raise RuntimeError("Failed to detect valid livery directories from extracted livery archive!")
            else:
              raise RuntimeError("Failed to extract livery archive[/bold red] \'" + livery.archive + "\'[bold red].")
        except Exception as e:
          installData['failed'].append({ 'url': correctedLiveryURL, 'error': e })
          self.console.print(e, style="bold red")
        finally:
          if livery:
            if livery.destination:
              self.console.print("Removing temporarily extracted folder.")
              self.lm.remove_extracted_livery_archive(livery)
            if livery.archive and not installArgs.keep:
              self.console.print("Removing downloaded archive file \'" + os.path.split(livery.archive)[1] + "\'.")
              self.lm.remove_downloaded_archive(livery, livery.archive)
          self.console.print("")
    if len(installData['success']):
      installTable = Table(title="Livery Install Report",expand=False, box=box.ROUNDED)
      installTable.add_column("Unit", justify="left", no_wrap=True, style="cyan")
      installTable.add_column("Livery Title", justify="left", style="green")
      installTable.add_column("# Liveries", justify="center", no_wrap=True, style="magenta")
      installTable.add_column("Size (MB)", justify="center", no_wrap=True, style="gold1")
      for l in installData['success']:
        installTable.add_row(Units.Units['aircraft'][l.dcsuf.unit]['friendly'], l.dcsuf.title, str(l.get_num_liveries()), "{:.2f}".format(float(l.get_size_installed_liveries()/(10**6))))
      self.console.print(installTable)
      self.lm.write_data()
    if len(installData['failed']):
      self.console.print("[bold red]Failed Livery Installs:")
      for l in installData['failed']:
        self.console.print("[bold red]" + l['url'] + "[/bold red][red]: " + str(l['error']))

  def check_liveries(self):
    # TODO: Make multi-threaded
    if not len(self.lm.LiveryData['liveries']):
      self.console.print("[red]No liveries registered to check.")
      return
    statusTable = Table(title="Livery Update Status", expand=True, box=box.ROUNDED)
    statusTable.add_column("Livery Title", justify="center", no_wrap=True)
    statusTable.add_column("Status", justify="center", no_wrap=True)
    with Live(statusTable, console=self.console, auto_refresh=True):
      for l in self.lm.Liveries.values():
        reqDCSUF = DCSUFParser().get_dcsuserfile_from_url(str(l.dcsuf.id))
        if l.dcsuf.datetime < reqDCSUF.datetime:
          statusTable.add_row(l.dcsuf.title, "[red]Out of date")
        else:
          statusTable.add_row(l.dcsuf.title, "[green]Up to date")

  def list_liveries(self):
    def sort_list_by_unit(e):
      return e[0]

    if not len(self.lm.LiveryData['liveries']):
      self.console.print("[red]No liveries registered to list.")
      return
    statusTable = Table(title="List of Registered Liveries", expand=True, box=box.ROUNDED, highlight=False)
    statusTable.add_column("Unit", justify="left", no_wrap=True, style="cyan")
    statusTable.add_column("Livery Title", justify="center", no_wrap=True, style="green")
    statusTable.add_column("ID", justify="center", no_wrap=True)
    liveryRows = []
    for l in self.lm.Liveries.values():
     liveryRows.append((Units.Units['aircraft'][l.dcsuf.unit]['friendly'], l.dcsuf.title, str(l.dcsuf.id)))
    liveryRows.sort(key=sort_list_by_unit)
    for l in liveryRows:
      statusTable.add_row(*l)
    self.console.print(statusTable)

  def func_test(self, sArgs):
    return None

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

  def print_dcsuf(self, livery):
    if livery:
      self.console.print(Panel("ID: " + str(livery.dcsuf.id) + " | Author: " + livery.dcsuf.author + " | Upload Date: " + livery.dcsuf.date + " | Archive Size: " + livery.dcsuf.size + " \n" + livery.dcsuf.download,
                               title=Units.Units['aircraft'][livery.dcsuf.unit]['friendly'] + " - " + livery.dcsuf.title,
                               expand=False, highlight=True))

  def print_livery(self, livery):
    if livery:
      self.console.print(Panel("tHIS IS A LIVERY PUT YOUR HANDS UP!", title=livery.ovgme,expand=False, highlight=True))

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
    self.console = Console(width=120, tab_size=4)
    #set_terminal_size(80, 50)

  def setup_livery_manager(self):
    self.lm = LiveryManager()
    lmData = self.lm.load_data()
    self.lm.make_dcslm_dirs()
    if not lmData:
      self.console.print("No existing dcslm.json file found with config and livery data. Loading defaults.")
      self.prompt_livery_manager_defaults()
      self.lm.write_data()
    else:
      self.console.print("Loaded Livery Manager config and data from DCSLM/dcslm.json")
      self.lm.LiveryData = lmData

  def prompt_livery_manager_defaults(self):
    if self.lm:
      self.console.print("\n\n[bold green underline]OVGME (Mod Manager) Mode:")
      self.console.print("If you use a mod manager, like OVGME, to manage your DCS mod installs, you can enable \'OVGME Mode\' to have it create a root directory named with the format [bold purple]{aircraft} - {livery title}[/bold purple].")
      self.console.print("\n[gold1]Make sure you've placed DCSLM.exe inside your mod manager's directory that is configured for the [/gold1]\'DCS Saved Games\'[gold1] directory, not the DCS install directory.[/gold1]")
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
      self.console.print("\nThere are multiple livery install locations for the [bold magenta]" + Units.Units['aircraft'][livery.dcsuf.unit]['friendly'] + "[/bold magenta]. Please choose from one of the following choices by inputting the corresponding index number:")
      self.console.print("\n\t" + choiceText)
      choice = Prompt.ask("\n[bold]Which aircraft do you want the livery to be installed to?[/bold]", choices=[str(i) for i in range(0,len(liveryChoices))])
      if choice == "0":
        choosenLiveries = unitLiveries
      else:
        choosenLiveries = [unitLiveries[int(choice) - 1]]
    return choosenLiveries

  def _download_archive_rich_callback(self, livery, dlCallback, downloadedBytes):
    dlCallback['progress'].update(dlCallback['task'], advance=downloadedBytes)

  def _download_archive_progress(self, livery):
    downloadProgress = Progress(TextColumn("[bold blue]{task.fields[filename]}", justify="right"),BarColumn(bar_width=None),"[progress.percentage]{task.percentage:>3.1f}%", "•",DownloadColumn(), "•", TransferSpeedColumn(), "•",TimeRemainingColumn(), console=self.console)
    archiveName = livery.dcsuf.download.split('/')[-1]
    dlTask = downloadProgress.add_task("download", filename=archiveName, start=False)
    dlSize = Utilities.request_file_size(livery.dcsuf.download)
    downloadProgress.update(dlTask, total=dlSize)
    callbackData = { 'exec': self._download_archive_rich_callback, 'progress': downloadProgress, 'task': dlTask }
    with downloadProgress:
      archivePath =  self.lm.download_livery_archive(livery, dlCallback=callbackData)
    return archivePath

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
        splitCommand = ' '.join(splitCommand).split()
        if len(splitCommand):
          if splitCommand[0] in self.commands:
            self.console.print("Running Command \'" + splitCommand[0] + "\'")
            commandData = self.commands[splitCommand[0]]
            argList = []
            if len(splitCommand) > 1:
              argList = splitCommand[1:]
            if commandData['exec']:
              #try:
                if len(commandData['args']):
                  commandData['exec'](sArgs=argList)
                else:
                  commandData['exec']()
              #except Exception as e:
                #self.console.print(e, style="bold red")
            if splitCommand[0] == "exit":
              runCommands = False
          else:
            self.console.print("Command \'" + splitCommand[0] + "\' not found.")
    self.console.print("Writing out current config and livery data to dcslm.json")
    self.lm.write_data()
    self.console.print("Exiting DCS Livery Manager.")


if __name__ == '__main__':
  #os.chdir(os.path.dirname(os.path.abspath(sys.executable)))
  os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))
  set_terminal_title(f'DCS Livery Manager v{__version__}')
  dcslmapp = DCSLMApp()
  dcslmapp.start()

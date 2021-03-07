from rich.console import Console
from rich.rule import Rule
from rich.prompt import Prompt
from rich.panel import Panel, Padding, PaddingDimensions
from rich.table import Table
from rich.console import RenderGroup
from rich.live import Live
from rich import box
from rich.align import Align
from rich.columns import Columns
from rich.progress import (
    BarColumn,
    DownloadColumn,
    TextColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
    Progress,
    TaskID,
    track,
    SpinnerColumn
)
import argparse
import os
import sys
import platform
import glob
from DCSLM import __version__
from prompt_toolkit import PromptSession, HTML
from prompt_toolkit.shortcuts import confirm
from prompt_toolkit.completion import WordCompleter, NestedCompleter
from DCSLM import Utilities
from DCSLM.Livery import DCSUserFile, Livery
from DCSLM.LiveryManager import LiveryManager, DCSLMFolderName
from DCSLM.UnitConfig import Units
from DCSLM.DCSUFParser import DCSUFParser


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
    self.console = None
    self.session = PromptSession(reserve_space_for_menu=6, complete_in_thread=True, )
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
        'desc': "Install DCS liveries from DCS User Files URLs or IDs.",
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
        'desc': "Uninstall the given managed livery from the \'title\' or \'ID\'.",
        'flags': {
          'keep': {
            'tags': ['-k', '--keep'],
            'desc': "Keep livery files on disk (untrack them)",
            'confirm': False
          },
        },
        'args': {
          'livery': {
            'type': "string",
            'optional': False,
            'desc': "DCS User Files livery title"
          },
        },
        'exec': self.uninstall_liveries
      },
      'info': {
        'completer': None,
        'usage': "livery",
        'desc': "Get additional info about an installed livery.",
        'flags': {},
        'args': {
          'livery': {
            'type': "string",
            'optional': False,
            'desc': "DCS User Files livery title"
          },
        },
        'exec': self.get_livery_info
      },
      'list': {
        'completer': None,
        'usage': "",
        'desc': "List currently installed DCS liveries.",
        'flags': {
          'ids': {
            'tags': ['ids'],
            'desc': "List the IDs of all registered liveries for copying.",
            'confirm': False
          },
        },
        'args': {},
        'exec': self.list_liveries
      },
      'check': {
        'completer': None,
        'usage': "",
        'desc': "Check for updates to any installed liveries.",
        'flags': {},
        'args': {},
        'exec': self.check_liveries
      },
      'update': {
        'completer': None,
        'usage': "",
        'desc': "Update any installed liveries that have a more recent version upload to \'DCS User Files\'.",
        'flags': {},
        'args': {},
        'exec': self.update_liveries
      },
      'scan': {
        'completer': None,
        'usage': "",
        'desc': "Scan folders for existing liveries with .dcslm registry files.",
        'flags': {},
        'args': {},
        'exec': self.scan_for_liveries
      },
      'help': {
        'completer': None,
        'usage': "",
        'desc': "List the commands and their usage.",
        'flags': {},
        'args': {},
        'exec': self.print_help
      },
      'exit': {
        'completer': None,
        'usage': "",
        'desc': "Exit the DCS Livery Manager program.",
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

  def _install_liveries(self, liveryStrings, keepFiles=False, forceDownload=False):
    installData = {'success': [], 'failed': []}
    # TODO: Check for duplicate url/IDs in list
    for liveryStr in liveryStrings:
      correctedLiveryURL = Utilities.correct_dcs_user_files_url(liveryStr)
      if not correctedLiveryURL:
        errorMsg = "Failed to get DCS User Files url or ID from \'" + liveryStr + "\'."
        installData['failed'].append({'url': liveryStr, 'error': errorMsg})
        self.console.print(errorMsg, style="bold red")
      else:
        livery = None
        try:
          getUFStr = "Getting DCS User File information from " + correctedLiveryURL
          with self.console.status(getUFStr):
            livery = self.lm.get_livery_data_from_dcsuf_url(correctedLiveryURL)
          self.console.print(getUFStr + "\n")
          self.print_dcsuf_panel(livery)
          unitLiveries = Units.Units['aircraft'][livery.dcsuf.unit]['liveries']
          if len(unitLiveries) > 1:
            unitLiveries = self.prompt_aircraft_livery_choice(livery, unitLiveries)
          livery.installs['units'] = unitLiveries
          archivePath = self.lm.does_archive_exist(livery.dcsuf.download.split('/')[-1])
          if archivePath:
            if not forceDownload and self.lm.compare_archive_sizes(archivePath, livery.dcsuf.download):
              self.console.print("\nArchive file \'" + livery.dcsuf.download.split('/')[-1] + "\' for \'" +
                                 livery.dcsuf.title + "\' already exists. Using that instead.")
            else:
              archivePath = None
          if not archivePath:
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
                liveryNames = [l['name'] for l in detectedLiveries]
                self.console.print(liveryNames)
                self.console.print("Generating livery install paths...")
                installPaths = self.lm.generate_livery_install_paths(livery, installRoots, detectedLiveries)
                if len(installPaths):
                  self.console.print("Installing " + str(len(detectedLiveries)) +
                                     (" liveries" if len(detectedLiveries) > 1 else " livery") + " to " +
                                     str(len(installRoots)) + " aircraft.")
                  with self.console.status("Installing extracted liveries..."):
                    copiedLiveries = self.lm.copy_detected_liveries(livery, extractPath,
                                                                    extractedLiveryFiles, installPaths)
                  if len(copiedLiveries):
                    with self.console.status("Writing registry files..."):
                      self.lm.write_livery_registry_files(livery)
                    self.console.print("Wrote " + str(len(installRoots) * len(detectedLiveries)) +
                                       " registry files to installed livery directories.")
                    self.lm.register_livery(livery)
                    self.console.print("[bold green]Livery[/bold green] \'" + str(livery.dcsuf.title) +
                                       "\' [bold green]Registered!")
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
          installData['failed'].append({'url': correctedLiveryURL, 'error': e})
          self.console.print(e, style="bold red")
        finally:
          if livery:
            if livery.destination:
              self.console.print("Removing temporarily extracted folder.")
              self.lm.remove_extracted_livery_archive(livery)
              # TODO: Check if failed to remove all files (desktop.ini, install 3314431)
            if livery.archive and not keepFiles:
              self.console.print("Removing downloaded archive file \'" + os.path.split(livery.archive)[1] + "\'.")
              self.lm.remove_downloaded_archive(livery, livery.archive)
          self.console.print("")
    return installData

  def _print_livery_install_report(self, installData, tableTitle):
    if len(installData['success']):
      installTable = Table(title=tableTitle,expand=False, box=box.ROUNDED)
      installTable.add_column("Unit", justify="left", no_wrap=True, style="cyan")
      installTable.add_column("Livery Title", justify="left", style="green")
      installTable.add_column("# Liveries", justify="center", no_wrap=True, style="magenta")
      installTable.add_column("Size (MB)", justify="right", no_wrap=True, style="gold1")
      for l in installData['success']:
        installTable.add_row(Units.Units['aircraft'][l.dcsuf.unit]['friendly'], l.dcsuf.title,
                             str(l.get_num_liveries()), Utilities.bytes_to_mb_string(l.get_size_installed_liveries()))
      self.console.print(installTable)
    if len(installData['failed']):
      self.console.print("[bold red]Failed Livery Installs:")
      for l in installData['failed']:
        self.console.print("[bold red]" + l['url'] + "[/bold red][red]: " + str(l['error']))
    self.console.print("")

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
    self.console.print("Attempting to install " + str(len(installArgs.url)) +
                       (" liveries" if len(installArgs.url) > 1 else " livery") + " from DCS User Files.")
    installData = self._install_liveries(installArgs.url, keepFiles=installArgs.keep)
    self.lm.write_data()
    self._print_livery_install_report(installData, "Livery Install Report")

  def _parse_uninstall_args(self, sArgs):
      installArgsParser = argparse.ArgumentParser(usage=self.commands['uninstall']['usage'],
                                                  description=self.commands['uninstall']['desc'],
                                                  exit_on_error=False)
      installArgsParser.add_argument(*self.commands['uninstall']['flags']['keep']['tags'], action="store_true",
                                     help=self.commands['uninstall']['flags']['keep']['desc'], dest='keep')
      installArgsParser.add_argument('livery', type=str, nargs="+",
                                     help=self.commands['uninstall']['args']['livery']['desc'])
      parsedArgs = installArgsParser.parse_known_args(sArgs)
      if len(parsedArgs[1]):
        self.console.print("Failed to parse the following args for \'uninstall\':", style="bold red")
        self.console.print("\t" + str(parsedArgs[1]), style="bold red")
      return parsedArgs[0]

  def uninstall_liveries(self, sArgs):
    uninstallArgs = self._parse_uninstall_args(sArgs)
    self.console.print("Attempting to uninstall " + str(len(uninstallArgs.livery)) +
                       (" registered liveries" if len(uninstallArgs.livery) > 1 else " registered livery") + ".")
    uninstallData = {'success': [], 'failed': []}
    # TODO: Check for duplicate liveries in list
    for liveryStr in uninstallArgs.livery:
      if str.isnumeric(liveryStr):
        try:
          self.console.print("Uninstalling \'" + liveryStr + "\'.")
          livery = self.lm.get_registered_livery(id=int(liveryStr))
          if (livery):
            self.console.print("Found registered livery.")
            numLiveries = str(livery.get_num_liveries())
            if uninstallArgs.keep:
              with self.console.status("Removing " + numLiveries + " livery registry files... (--keep)"):
                self.lm.uninstall_livery(livery)
              self.console.print("Removed " + numLiveries + " livery registry files. (--keep)")
            else:
              with self.console.status("Removing " + numLiveries + " installed livery directories..."):
                self.lm.uninstall_livery(livery)
              self.console.print("Removed " + numLiveries + " installed livery directories.")
            uninstallData['success'].append(livery)
            self.console.print("Successfully uninstalled livery \'" + livery.dcsuf.title + "\'.")
          else:
            raise RuntimeError("Livery \'" + liveryStr + "\' not found in livery registry.")
        except Exception as e:
          uninstallData['failed'].append({'livery': liveryStr, 'error': e})
          self.console.print(e, style="bold red")
        finally:
          self.console.print("")
    if len(uninstallData['success']):
      self.console.print("[bold green]Successful Livery Uninstalls:")
      for l in uninstallData['success']:
        self.console.print("\t(" + str(l.dcsuf.id) + ") " + l.dcsuf.title, highlight=False)
      self.lm.write_data()
    if len(uninstallData['failed']):
      self.console.print("[bold red]Failed Livery Uninstalls:")
      for l in uninstallData['failed']:
        self.console.print("\t(" + l['livery'] + "[red]: " + str(l['error']))

  def _check_all_liveries_updates(self, verbose=False):
    # TODO: Make multi-threaded
    liveryStatus = []
    checkProgress = Progress("[progress.description]{task.description}",
                             SpinnerColumn(spinner_name="dots"),
                             BarColumn(),
                             "{task.completed}/{task.total}",
                             console=self.console)
    checkTask = checkProgress.add_task("Checking liveries for updates", total=len(self.lm.Liveries.keys()))
    with checkProgress:
      for l in self.lm.Liveries.values():
        reqDCSUF = DCSUFParser().get_dcsuserfile_from_url(str(l.dcsuf.id))
        if l.dcsuf.datetime < reqDCSUF.datetime:
          liveryStatus.append({'livery': l, 'update': True})
          if verbose:
            checkProgress.print("Found update for livery \'" + l.dcsuf.title + "\'!")
        else:
          liveryStatus.append({'livery': l, 'update': False})
        checkProgress.update(checkTask, advance=1)
    return liveryStatus

  def check_liveries(self):
    if not len(self.lm.Liveries.keys()):
      self.console.print("[red]No liveries registered to check.")
      return
    liveryStatus = self._check_all_liveries_updates()
    statusTable = Table(title="Livery Update Status", expand=True, box=box.ROUNDED)
    statusTable.add_column("Livery Title", justify="center", no_wrap=True)
    statusTable.add_column("Status", justify="center", no_wrap=True)
    numToUpdate = 0
    for l in liveryStatus:
      if l['update']:
        statusTable.add_row(l['livery'].dcsuf.title, "[red]Out of date")
        numToUpdate += 1
      else:
        statusTable.add_row(l['livery'].dcsuf.title, "[green]Up to date")
    self.console.print(statusTable)
    if numToUpdate > 0:
      if numToUpdate > 1:
        self.console.print(str(numToUpdate) + " liveries have updates! Run the \'update\' command to get " +
                           "the latest versions from \'DCS User Files\'.")
      else:
        self.console.print(str(numToUpdate) + " livery has an update! Run the \'update\' command to get " +
                           "the latest version from \'DCS User Files\'.")

  def update_liveries(self):
    if not len(self.lm.Liveries.keys()):
      self.console.print("[red]No liveries registered to update.")
      return
    liveryStatus = self._check_all_liveries_updates(verbose=True)
    updateList = []
    for l in liveryStatus:
      if l['update']:
        updateList.append(str(l['livery'].dcsuf.id))
    if not len(updateList):
      self.console.print("[red]No liveries need updating.")
      return
    self.console.print("Found " + str(len(updateList)) + " liveries that need updating.")
    self.console.print("")
    updateData = self._install_liveries(updateList, forceDownload=True)
    self.lm.write_data()
    self._print_livery_install_report(updateData, "Livery Update Report")

  def list_liveries(self, sArgs):
    def sort_list_by_unit_then_title(e):
      return e[0] + " - " + e[1]

    if not len(self.lm.Liveries.keys()):
      self.console.print("[red]No liveries registered to list.")
      return

    if len(sArgs):
      if len(sArgs) == 1 and sArgs[0] == "ids":
        self.console.print("Printing the IDs of " + str(len(self.lm.Liveries)) + " registered liveries.")
        self.console.print(' '.join([l for l in self.lm.Liveries.keys()]))
        return
    liveryRows = []
    longestUnit = ""
    for l in self.lm.Liveries.values():
      friendlyUnit = Units.Units['aircraft'][l.dcsuf.unit]['friendly']
      liveryRows.append((friendlyUnit, str(l.dcsuf.id), l.dcsuf.title,
                         Utilities.bytes_to_mb_string(l.get_size_installed_liveries())))
      if len(friendlyUnit) > len(longestUnit):
        longestUnit = friendlyUnit
    unitColWidth = max(8, min(13, len(longestUnit)))
    statusTable = Table(title="List of Registered Liveries", expand=True, box=box.ROUNDED, highlight=False)
    statusTable.add_column("Unit", justify="center", no_wrap=True, style="cyan", width=unitColWidth)
    statusTable.add_column("ID", justify="center", no_wrap=True, style="green", width=11)
    statusTable.add_column("Livery Title", justify="center", no_wrap=True, overflow='ellipsis')
    statusTable.add_column("Size", justify="right", no_wrap=True, style="gold1", width=10)

    liveryRows.sort(key=sort_list_by_unit_then_title)
    for i in range(0, len(liveryRows)):
      l = liveryRows[i]
      isEndSection = False
      if i != len(liveryRows) - 1:
        nextUnit = nextL = liveryRows[i + 1][0]
        if nextUnit != l[0]:
          isEndSection = True
      if i == len(liveryRows) - 1: # for footer
        isEndSection = True
      statusTable.add_row(*l, end_section=isEndSection)
    #statusTable.add_row("3 Units", "47 Registered Liveries with 100 Installed Livery Directories",
    #                    "3.02 GB", end_section=True)
    self.console.print(statusTable)

  def _make_livery_rendergroup(self, livery):
    liveryTable = Table.grid(expand=True, padding=(0,2,2,0), pad_edge=True)
    liveryTable.add_column("Info", justify="right", no_wrap=True)
    liveryTable.add_column("Content", justify="left")
    archiveStyle = "[red]"
    if os.path.isfile(livery.archive):
      archiveStyle = "[green]"
    liveryTable.add_row("Archive", archiveStyle + livery.archive)
    if self.lm.LiveryData['config']['ovgme']:
      liveryTable.add_row("OVGME Directory", livery.ovgme)
    liveryTable.add_row("Destination", livery.destination)
    liveryTable.add_row("Units", "[" + ', '.join(livery.installs['units']) + "]")
    liveryTable.add_row("Liveries", "[" + ', '.join(livery.installs['liveries'].keys()) + "]")
    installs = []
    for l,i in livery.installs['liveries'].items():
      installs.extend(i['paths'])
    liveryTable.add_row("Paths", str(installs))
    liveryRG = liveryTable
    return liveryRG

  def get_livery_info(self, sArgs):
    if len(sArgs) == 1:
      liveryID = sArgs[0]
      livery = self.lm.get_registered_livery(id=liveryID)
    else:
      liveryName = ' '.join(sArgs)
      livery = self.lm.get_registered_livery(title=liveryName)
    if livery:
      dcsufPanel = self._make_dcsuf_panel(livery)
      dcsufPanel.title = "DCS User Files Information"
      dcsufPanel.title_align = "left"
      dcsufAlign = Align(dcsufPanel, align="center")
      liveryRG = self._make_livery_rendergroup(livery)
      liveryAlign = Align(liveryRG, align="center")
      liveryInfoPanelGroup = RenderGroup(dcsufAlign, liveryAlign)
      self.console.print(Panel(liveryInfoPanelGroup, title=livery.dcsuf.title + " Livery Info", highlight=True))
    return

  def scan_for_liveries(self):
    with self.console.status("Scanning directories for DCSLM installed liveries..."):
      liveryFolders = []
      rootFolders = glob.glob("./*/")
      if self.lm.LiveryData['config']['ovgme']:
        self.console.print("Scanning for \'OVGME\' directories with .dcslm registry files...")
        for f in rootFolders:
          cDirs = glob.glob(f + "*/")
          for c in cDirs:
            if "\\Liveries\\" in c:
              liveryFolders.append(c)
      else:
        self.console.print("Scanning \'Livery\' directory for unit liveries with .dcslm registry files...")
        for f in rootFolders:
          if "\\Liveries\\" in f:
            liveryFolders.append(f)
      self.console.print("Found " + str(len(liveryFolders)) + " directories with a \'Liveries\' subdirectory.")
      unitFolders = []
      for lF in liveryFolders:
        unitDirs = glob.glob(lF + "*/")
        for uD in unitDirs:
          splitUDPath = str.split(uD, '\\')
          if len(splitUDPath) >= 2:
            unitName = str.split(uD, '\\')[-2]
            unit = Units.get_unit_from_liveries_dir(unitName)
            if unit:
              unitFolders.append(uD)
      self.console.print("Matched " + str(len(unitFolders)) + " known unit directories.")
      installedDCSLMFiles = []
      for uF in unitFolders:
        livDirs = glob.glob(uF + "/*/")
        for lD in livDirs:
          regFiles = glob.glob(lD + ".dcslm*")
          if regFiles:
            installedDCSLMFiles.append(regFiles[0])
      self.console.print("Found " + str(len(installedDCSLMFiles)) + " \'.dcslm\' registry files.")
      registeredLiveries = {'success':{}, 'failed':[], 'existing':{}}
      for dF in installedDCSLMFiles:
        livery = self.lm.load_livery_from_livery_registry_file(dF)
        if livery:
          if not self.lm.is_livery_registered(livery=livery):
            self.lm.register_livery(livery)
            registeredLiveries['success'][livery.dcsuf.id] = livery
          else:
            if livery not in registeredLiveries['success']:
              registeredLiveries['existing'][livery.dcsuf.id] = livery
        else:
          registeredLiveries['failed'].append(dF)
      reportStr = ""
      if len(registeredLiveries['success']):
        reportStr += "Registered " + str(len(registeredLiveries['success'])) + " missing liveries. "
      if len(registeredLiveries['existing']):
        reportStr += "Matched " + str(len(registeredLiveries['existing'])) + " existing registered liveries. "
      if len(registeredLiveries['failed']):
        reportStr += "Failed to register " + str(len(registeredLiveries['failed'])) + " liveries from \'.dcslm\' files:\n"
        reportStr += ', '.join(registeredLiveries['failed'])
      self.lm.write_data()
      self.console.print(reportStr)

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

  def _make_dcsuf_panel(self, livery):
    return Panel("ID: " +
                 str(livery.dcsuf.id) + " | Author: " + livery.dcsuf.author + " | Upload Date: " +
                     livery.dcsuf.date + " | Archive Size: " + livery.dcsuf.size + " \n" + livery.dcsuf.download,
                     title=Units.Units['aircraft'][livery.dcsuf.unit]['friendly'] + " - " + livery.dcsuf.title,
                     expand=False, highlight=True)

  def print_dcsuf_panel(self, livery):
    if livery:
      self.console.print(self._make_dcsuf_panel(livery))

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
    self.console.print(
           Rule(f'[bold gold1]DCS Livery Manager[/bold gold1] [bold sky_blue1]v{__version__}[/bold sky_blue1]',
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
      self.console.print("No existing \'DCSLM/dcslm.json\' file found with config and livery data. Loading defaults.")
      self.prompt_livery_manager_defaults()
      self.lm.write_data()
    else:
      self.console.print("Loaded Livery Manager config and data from \'DCSLM/dcslm.json\'")
      self.lm.LiveryData = lmData

  def prompt_livery_manager_defaults(self):
    if self.lm:
      self.console.print("\n\n[bold green underline]OVGME (Mod Manager) Mode:")
      self.console.print("If you use a mod manager, like OVGME, to manage your DCS mod installs, you can enable " +
                         "\'OVGME Mode\' to have it create a root directory named with the format " +
                         "[bold purple]{aircraft} - {livery title}[/bold purple].")
      self.console.print("\n[gold1]Make sure you've placed \'DCSLM.exe\' inside your mod manager's directory that is " +
                         "configured for the [/gold1]\'DCS Saved Games\'[gold1] directory, " +
                         "not the DCS install directory.[/gold1]")
      ovgme = Prompt.ask("\n[bold]Do you want to enable OVGME (Mod Manager) Mode?[/bold]", choices=["Yes", "No"])
      ovgme = (True if ovgme == "Yes" else False)
      self.lm.LiveryData['config']['ovgme'] = ovgme
      if ovgme:
        self.console.print("[green]Enabling OVGME (Mod Manager) mode.")

  def prompt_aircraft_livery_choice(self, livery, unitLiveries):
    # TODO: Add choice for none
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
      self.console.print("\nThere are multiple livery install locations for the [bold magenta]" +
                         Units.Units['aircraft'][livery.dcsuf.unit]['friendly'] + "[/bold magenta]. " +
                         "Please choose from one of the following choices by inputting the corresponding index number:")
      self.console.print("\n\t" + choiceText)
      choice = Prompt.ask("\n[bold]Which aircraft do you want the livery to be installed to?[/bold]",
                          choices=[str(i) for i in range(0,len(liveryChoices))])
      if choice == "0":
        choosenLiveries = unitLiveries
      else:
        choosenLiveries = [unitLiveries[int(choice) - 1]]
    return choosenLiveries

  def _download_archive_rich_callback(self, livery, dlCallback, downloadedBytes):
    dlCallback['progress'].update(dlCallback['task'], advance=downloadedBytes)

  def _download_archive_progress(self, livery):
    downloadProgress = Progress(TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
                                BarColumn(bar_width=None),"[progress.percentage]{task.percentage:>3.1f}%",
                                "•",DownloadColumn(), "•", TransferSpeedColumn(), "•",TimeRemainingColumn(),
                                console=self.console)
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
        command = self.session.prompt(HTML("<ansibrightcyan>DCSLM></ansibrightcyan> "), completer=self.completer)
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
                if len(commandData['args']) or len(commandData['flags']):
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

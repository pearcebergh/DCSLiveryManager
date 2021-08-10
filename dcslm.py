import argparse
import glob
import os
import platform
import sys
from pprint import pprint
from prompt_toolkit import PromptSession, HTML
from prompt_toolkit.completion import NestedCompleter
from rich import box
from rich.align import Align
from rich.console import Console, RenderGroup
from rich.columns import Columns
from rich.panel import Panel
from rich.progress import (
  BarColumn,
  DownloadColumn,
  TextColumn,
  TransferSpeedColumn,
  TimeRemainingColumn,
  Progress,
  SpinnerColumn
)
from rich.prompt import Prompt, Confirm
from rich.rule import Rule
from rich.status import Status
from rich.table import Table
from DCSLM import __version__
from DCSLM.DCSUFParser import DCSUFParser
from DCSLM.Livery import DCSUserFile, Livery
from DCSLM.LiveryManager import LiveryManager
from DCSLM.UnitConfig import Units
import DCSLM.Utilities as Utilities

def set_console_title(title):
  if platform.system() == 'Windows':
    os.system(f'title {title}')
  else:
    os.system(f'echo "\033]0;{title}\007"')

def clear_console():
  if platform.system() == 'Windows':
    os.system('cls')
  else:
    os.system('clear')

def set_console_size(w, h):
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
    self.quick_check_upgrade_available()
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
            'action': "store_true",
            'confirm': False
          },
          'reinstall': {
            'tags': ['-r', '--reinstall'],
            'desc': "Do not prompt if the livery is already registered.",
            'action': "store_true",
            'confirm': False
          },
          'allunits': {
            'tags': ['-a', '--allunits'],
            'desc': "Do not prompt when given a choice to install to multiple units and install to all.",
            'action': "store_true",
            'confirm': False
          },
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
            'action': "store_true",
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
            'action': "store_true",
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
      'optimize': {
        'completer': None,
        'usage': "\[flags] livery",
        'desc': "Attempt to optimize an installed livery by looking for unused or shared files between liveries within packs.",
        'flags': {
          'reoptimize': {
            'tags': ['-r','--reoptimize'],
            'desc': "Optimize liveries even if they have already been optimized.",
            'action': "store_true",
            'confirm': False
          },
          'keepdesc': {
            'tags': ['-d','--keepdesc'],
            'desc': "Keep a copy of the original unmodified description.lua files.",
            'action': "store_true",
            'confirm': False
          },
          'keepunused': {
            'tags': ['-u', '--keepunused'],
            'desc': "Keep unused files on disk at the end of optimization.",
            'action': "store_true",
            'confirm': False
          },
          'verbose': {
            'tags': ['-v', '--verbose'],
            'desc': "Verbose printing of livery file reference data for debugging purposes.",
            'action': "store_true",
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
        'exec': self.optimize_livery
      },
      'scan': {
        'completer': None,
        'usage': "",
        'desc': "Scan folders for existing liveries with .dcslm registry files.",
        'flags': {},
        'args': {},
        'exec': self.scan_for_liveries
      },
      'upgrade': {
        'completer': None,
        'usage': "",
        'desc': "Upgrade DCSLM to the latest version",
        'flags': {},
        'args': {},
        'exec': self.upgrade_dcslm
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
      }
    }

  def _install_liveries(self, liveryStrings, keepFiles=False, forceDownload=False, forceInstall=False, forceAllUnits=False):
    installData = {'success': [], 'failed': []}
    for liveryStr in liveryStrings:
      correctedLiveryURL, urlID = Utilities.correct_dcs_user_files_url(liveryStr)
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
          existingLivery = self.lm.get_registered_livery(id=int(urlID))
          if existingLivery and not forceInstall:
            if existingLivery.dcsuf.datetime == livery.dcsuf.datetime:
              if not self.prompt_existing_livery(existingLivery):
                raise RuntimeError("Skipping reinstalling livery.")
          unitLiveries = Units.Units['aircraft'][livery.dcsuf.unit]['liveries']
          if len(unitLiveries) > 1 and not forceAllUnits:
            unitLiveries = self.prompt_aircraft_livery_choice(livery, unitLiveries)
          if len(unitLiveries) == 0:
            raise RuntimeError("No units selected for install.")
          livery.installs['units'] = unitLiveries
          archivePath = self.lm.does_archive_exist(livery.dcsuf.download.split('/')[-1])
          if archivePath:
            if not forceDownload and self.lm.compare_archive_sizes(archivePath, livery.dcsuf.download):
              self.console.print("\nArchive file \'" + livery.dcsuf.download.split('/')[-1] + "\' for \'" +
                                 livery.dcsuf.title + "\' already exists. Using that instead.")
              keepFiles = True
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
              raise RuntimeError("Failed to extract livery archive \'" + livery.archive + "\'.")
        except Exception as e:
          installData['failed'].append({'url': correctedLiveryURL, 'error': e})
          self.console.print(e, style="bold red")
        finally:
          if livery:
            if livery.destination:
              self.console.print("Removing temporarily extracted folder.")
              if not self.lm.remove_extracted_livery_archive(livery):
                failedExtractPath = os.path.join(os.getcwd(), self.lm.FolderRoot, "extract", str(livery.dcsuf.id))
                failedMsg = "Failed to remove all extracted files to directory " + failedExtractPath
                self.console.print(failedMsg, style="red")
                installData['failed'].append({'url': livery.dcsuf.id, 'error': failedMsg})
            if livery.archive and not keepFiles:
              self.console.print("Removing downloaded archive file \'" + os.path.split(livery.archive)[1] + "\'.")
              self.lm.remove_downloaded_archive(livery, livery.archive)
          self.console.print("")
    return installData

  def _print_livery_install_report(self, installData, tableTitle):
    if len(installData['success']):
      installTable = Table(title=tableTitle,expand=False, box=box.ROUNDED)
      installTable.add_column("Unit", justify="left", no_wrap=True, style="green")
      installTable.add_column("ID", justify="center", no_wrap=True, style="sky_blue1")
      installTable.add_column("Livery Title", justify="center", style="")
      installTable.add_column("# Liveries", justify="center", no_wrap=True, style="magenta")
      installTable.add_column("Size (MB)", justify="right", no_wrap=True, style="bold gold1")
      for l in installData['success']:
        installTable.add_row(Units.Units['aircraft'][l.dcsuf.unit]['friendly'], str(l.dcsuf.id), l.dcsuf.title,
                             str(l.get_num_liveries()), Utilities.bytes_to_mb_string(l.get_size_installed_liveries()))
      self.console.print(installTable)
    if len(installData['failed']):
      self.console.print("[bold red]Failed Livery Installs:")
      for l in installData['failed']:
        self.console.print("[bold red]" + l['url'] + "[/bold red][red]: " + str(l['error']))

  def _parse_install_args(self, sArgs):
    try:
      installArgsParser = argparse.ArgumentParser(usage=self.commands['install']['usage'],
                                                  description=self.commands['install']['desc'],
                                                  exit_on_error=False)
      for iA in self.commands['install']['flags'].keys():
        installArgsParser.add_argument(*self.commands['install']['flags'][iA]['tags'],
                                        help=self.commands['install']['flags'][iA]['desc'],
                                        action=self.commands['install']['flags'][iA]['action'], dest=iA)
      installArgsParser.add_argument('url', type=str, help=self.commands['install']['args']['url']['desc'], nargs="+")
      parsedArgs = installArgsParser.parse_known_args(sArgs)
      if len(parsedArgs[1]):
        self.console.print("Failed to parse the following args for \'install\':", style="bold red")
        self.console.print("\t" + str(parsedArgs[1]), style="bold red")
      return parsedArgs[0]
    except SystemExit:
      raise RuntimeError("Unable to parse \'uninstall\' command.")

  def install_liveries(self, sArgs):
    installArgs = self._parse_install_args(sArgs)
    self.console.print("Attempting to install " + str(len(installArgs.url)) +
                       (" liveries" if len(installArgs.url) > 1 else " livery") + " from DCS User Files.")
    installData = self._install_liveries(installArgs.url, keepFiles=installArgs.keep,
                                         forceInstall=installArgs.reinstall, forceAllUnits=installArgs.allunits)
    self.lm.write_data()
    self._print_livery_install_report(installData, "Livery Install Report")
    self.console.print("")

  def _parse_uninstall_args(self, sArgs):
    try:
      uninstallArgsParser = argparse.ArgumentParser(usage=self.commands['uninstall']['usage'],
                                                  description=self.commands['uninstall']['desc'],
                                                  exit_on_error=False)
      uninstallArgsParser.add_argument(*self.commands['uninstall']['flags']['keep']['tags'], action="store_false",
                                     help=self.commands['uninstall']['flags']['keep']['desc'], dest='keep')
      uninstallArgsParser.add_argument('livery', type=str, nargs="+",
                                     help=self.commands['uninstall']['args']['livery']['desc'])
      parsedArgs = uninstallArgsParser.parse_known_args(sArgs)
      if len(parsedArgs[1]):
        self.console.print("Failed to parse the following args for \'uninstall\':", style="bold red")
        self.console.print("\t" + str(parsedArgs[1]), style="bold red")
      return parsedArgs[0]
    except SystemExit:
      raise RuntimeError("Unable to parse \'uninstall\' command.")

  def uninstall_liveries(self, sArgs):
    uninstallArgs = self._parse_uninstall_args(sArgs)
    self.console.print("Attempting to uninstall " + str(len(uninstallArgs.livery)) +
                       (" registered liveries" if len(uninstallArgs.livery) > 1 else " registered livery") + ".")
    uninstallData = {'success': [], 'failed': []}
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
        self.console.print("\t" + l['livery'] + "[red]: " + str(l['error']))
    self.console.print("")

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
      liveryStr = " livery"
      if numToUpdate > 1:
        liveryStr = " liveries"
      self.console.print(str(numToUpdate) + liveryStr + " have updates! Run the \'update\' command to get " +
                         "the latest versions from \'DCS User Files\'.")

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
    self.console.print("")

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
    footerData = {'size': 0, 'units': [], 'installed': 0, 'registered': 0}
    for l in self.lm.Liveries.values():
      friendlyUnit = Units.Units['aircraft'][l.dcsuf.unit]['friendly']
      liverySizeMB = Utilities.bytes_to_mb(l.get_size_installed_liveries())
      footerData['size'] += liverySizeMB
      footerData['registered'] += 1
      footerData['installed'] += l.get_num_liveries()
      if l.dcsuf.unit not in footerData['units']:
        footerData['units'].append(l.dcsuf.unit)
      liveryRows.append((friendlyUnit, str(l.dcsuf.id), l.dcsuf.title,
                         Utilities.mb_to_mb_string(liverySizeMB)))
      if len(friendlyUnit) > len(longestUnit):
        longestUnit = friendlyUnit
    unitColWidth = max(8, min(13, len(longestUnit)))
    statusTable = Table(title="List of Registered Liveries", expand=True, box=box.ROUNDED, highlight=False)
    statusTable.add_column("Unit", justify="center", no_wrap=True, style="green", width=unitColWidth)
    statusTable.add_column("ID", justify="center", no_wrap=True, style="sky_blue1", width=8)
    statusTable.add_column("Livery Title", justify="center", no_wrap=True, overflow='ellipsis')
    statusTable.add_column("Size", justify="right", no_wrap=True, style="bold gold1", width=10)
    liveryRows.sort(key=sort_list_by_unit_then_title)
    for i in range(0, len(liveryRows)):
      l = liveryRows[i]
      isEndSection = False
      if i != len(liveryRows) - 1:
        nextUnit = liveryRows[i + 1][0]
        if nextUnit != l[0]:
          isEndSection = True
      if i == len(liveryRows) - 1: # for footer
        isEndSection = True
      statusTable.add_row(*l, end_section=isEndSection)
    footerString = str(footerData['registered']) + " Registered Liveries    " + str(footerData['installed']) + \
                   " Installed Livery Directories    " + str(len(footerData['units'])) + " Units    Total Size: " + \
                   Utilities.mb_to_mb_string(footerData['size']) + " MB"
    self.console.print(statusTable)
    self.console.print(footerString, justify="center")
    self.console.print("")

  def _make_livery_rendergroup(self, livery):
    liveryTable = Table.grid(expand=True, padding=(0,2,2,0), pad_edge=True)
    liveryTable.add_column("Info", justify="right", no_wrap=True)
    liveryTable.add_column("Content", justify="left")
    archiveStyle = "[red]"
    if os.path.isfile(livery.archive):
      archiveStyle = "[green]"
    liveryTable.add_row("Archive", archiveStyle + livery.archive)
    if self.lm.LiveryData['config']['ovgme']:
      liveryTable.add_row("Mod Managed Directory", livery.ovgme)
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
      self.console.print("")

  def quick_check_upgrade_available(self):
    relData = self.request_upgrade_information()
    if relData:
      if len(relData):
        self.console.print("\nYour DCSLM [bold red]v" + str(__version__) + "[/bold red] is out of date!\n" +
                           "Use the \'upgrade\' command to upgrade DCSLM to [bold green]v" + relData[0]['version'] + "[/bold green]")

  def request_upgrade_information(self):
    import re
    import requests
    from distutils.version import StrictVersion
    from bs4 import BeautifulSoup
    try:
      releaseData = []
      relReq = requests.get("https://github.com/pearcebergh/DCSLiveryManager/releases", timeout=5)
      relHTML = BeautifulSoup(relReq.text, 'html.parser')
      relDivs = relHTML.find_all('div', {'class': "release-entry"})
      for r in relDivs:
        rData = {}
        rData['name'] = r.find('div', {'class': "f1 flex-auto min-width-0 text-normal"}).text[:-1]
        rData['version'] = r.find('span', {'class': "css-truncate-target"}).text
        rData['desc'] = r.find('div', {'class': "markdown-body"}).text
        rData['date'] = r.find('relative-time').text
        rData['download'] = "https://github.com/" + r.find('a', {'class': "d-flex flex-items-center min-width-0"},
                                                           href=re.compile(r'[/]([a-z]|[A-Z])\w+')).attrs['href']
        if StrictVersion(rData['version']) > StrictVersion(__version__):
          releaseData.append(rData)
      return releaseData
    except Exception as e:
      raise e

  def upgrade_dcslm(self):
    import shutil
    import time
    import requests
    import subprocess
    try:
      releaseData = self.request_upgrade_information()
      if not len(releaseData):
        self.console.print("Current DCSLM version " + __version__ + " is the available latest version.")
      else:
        for rd in releaseData:
          self.console.print(rd['name'] + " (" + rd['version'] + ") " + rd['date'] + ":")
          splitDesc = str.split(rd['desc'], '\n')
          for descLine in splitDesc:
            if len(descLine):
              self.console.print(" - " + descLine)
        self.console.print("")
        upgradeConf = Confirm.ask("Do you want to download and upgrade to the latest version of DCSLM?")
        self.console.print("")
        if upgradeConf:
          oldExec = sys.executable + '.old'
          if os.path.isfile(oldExec):
            try:
              Utilities.remove_file(oldExec)
              # os.remove(oldExec)
            except Exception as e:
              self.console.print("[bold red]Failed to remove old executable:[/bold red] [red]" + str(e))
          shutil.move(sys.executable, oldExec)
          dlFilename = "DCSLM.exe"
          with self.console.status("Downloading DCSLM v" + releaseData[0]['version']):
            latestExe = requests.get(releaseData[0]['download'], timeout=5)
          with open(dlFilename, 'wb') as f:
            f.write(latestExe.content)
          os.chmod(dlFilename, 0o775)
          self.console.print("[bold green]DCSLM Upgrade complete to version " + releaseData[0]['version'])
          self.console.print("[bold red]DCSLM will be restarted in a few moments...")
          time.sleep(2.5)
          subprocess.call(dlFilename)
          sys.exit(0)
    except Exception as e:
      self.console.print("[bold red]DCSLM upgrade failed:[/bold red] [red]" + str(e))

  def _print_optimization_report(self, optimizationReport):
    if len(optimizationReport):
      optimizationTable = Table(title="Livery Optimization Report", expand=True, box=box.ROUNDED)
      optimizationTable.add_column("ID", justify="center", no_wrap=True, style="sky_blue1")
      optimizationTable.add_column("Livery Title", justify="center", style="")
      optimizationTable.add_column("# Liveries", justify="center", style="magenta")
      optimizationTable.add_column("Hash Matches", justify="center", no_wrap=False, style="green")
      optimizationTable.add_column("Size Before (MB)", justify="right", no_wrap=False, style="gold1")
      optimizationTable.add_column("Size After (MB)", justify="right", no_wrap=False, style="bold gold1")
      totalSizeBefore, totalSizeAfter, totalSizeDelta = 0.0, 0.0, 0.0
      for op in optimizationReport:
        l = op['livery']
        sb = Utilities.bytes_to_mb(op['size_before'])
        sa = Utilities.bytes_to_mb(op['size_after'])
        totalSizeBefore += sb
        totalSizeAfter += sa
        totalSizeDelta += sa - sb
        optimizationTable.add_row(str(l.dcsuf.id), l.dcsuf.title, str(l.get_num_liveries()), str(op['matches']),
                                  Utilities.mb_to_mb_string(sb),
                                  Utilities.mb_to_mb_string(sa))
      self.console.print(optimizationTable)
      self.console.print("Total Size Before: " + Utilities.mb_to_mb_string(totalSizeBefore) +
                         " Mb    Total Size After: " + Utilities.mb_to_mb_string(totalSizeAfter) +
                         " Mb    Total Size Delta: " + Utilities.mb_to_mb_string(totalSizeDelta) + " Mb",
                         justify="center")

  def _parse_optimize_args(self, sArgs):
    try:
      optimizeArgsParser = argparse.ArgumentParser(usage=self.commands['optimize']['usage'],
                                                   description=self.commands['optimize']['desc'],
                                                   exit_on_error=False)
      for oA in self.commands['optimize']['flags'].keys():
        optimizeArgsParser.add_argument(*self.commands['optimize']['flags'][oA]['tags'],
                                        help=self.commands['optimize']['flags'][oA]['desc'],
                                        action=self.commands['optimize']['flags'][oA]['action'], dest=oA)
      optimizeArgsParser.add_argument('livery', type=str, nargs="+",
                                      help=self.commands['optimize']['args']['livery']['desc'])
      parsedArgs = optimizeArgsParser.parse_known_args(sArgs)
      if len(parsedArgs[1]):
        self.console.print("Failed to parse the following args for \'optimize\':", style="bold red")
        self.console.print("\t" + str(parsedArgs[1]), style="bold red")
      return parsedArgs[0]
    except SystemExit:
      raise RuntimeError("Unable to parse \'optimize\' command.")

  # 3314521 (lua ref missing file)
  def optimize_livery(self, sArgs):
    if not len(sArgs):
      raise RuntimeWarning("No liveries provided for \'optimize\' command.")
    optimizeArgs = self._parse_optimize_args(sArgs)
    removeFiles = True
    optimizationReports = []
    liveryIDs = []
    if len(optimizeArgs.livery) == 1 and str.lower(optimizeArgs.livery[0]) == "all":
      self.console.print("Attempting to optimize all installed liveries...")
      liveryIDs = self.lm.get_registered_livery_ids()
    else:
      for l in optimizeArgs.livery:
        if l not in liveryIDs:
          liveryIDs.append(l)
    for l in liveryIDs:
      livery = self.lm.get_registered_livery(id=l)
      if livery:
        if not 'optimized' in livery.installs.keys() or not livery.installs['optimized'] or optimizeArgs.reoptimize:
          self.console.print("Optimizing livery \'" + livery.dcsuf.title + "\'")
          filesData = self.lm.optimize_livery(livery, copyDesc=optimizeArgs.keepdesc, removeUnused=not optimizeArgs.keepunused)
          if filesData:
            livery.installs['optimized'] = True
            optimizationData = {'matches': len(filesData['same_hash']),
                                'size_before': filesData['size']['before'],
                                'size_after': filesData['size']['after'],
                                'livery': livery}
            optimizationReports.append(optimizationData)
            liveryReportStr = "Matched " + str(len(filesData['same_hash'])) + " .dds files with the same content."
            if removeFiles:
              liveryReportStr += " Removed " + str(len(filesData['unused'])) + " unused files.\n"
              liveryReportStr += "Size Before: " + Utilities.bytes_to_mb_string(filesData['size']['before']) + " Mb\t"
              liveryReportStr += "Size After: " + Utilities.bytes_to_mb_string(filesData['size']['after']) + " Mb\t"
              liveryReportStr += "Size Delta: " + Utilities.bytes_to_mb_string(filesData['size']['after'] - filesData['size']['before']) + " Mb"
            self.console.print(liveryReportStr)
            self.console.print("")
            if optimizeArgs.verbose:
              pprint(filesData)
        else:
          self.console.print("Skipping re-optimizing livery \'" + livery.dcsuf.title + "\'.")
      else:
        self.console.print("No livery found for input \'" + l + "\'.")
    with self.console.status("Updating livery .dcslm files..."):
      for op in optimizationReports:
        l = op['livery']
        self.lm.write_livery_registry_files(l)
      self.lm.write_data()
    self._print_optimization_report(optimizationReports)
    self.console.print("")

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
    self.console.print("")

  def _make_dcsuf_panel(self, livery):
    return Panel("ID: " +
                 str(livery.dcsuf.id) + " | Author: " + livery.dcsuf.author + " | Upload Date: " +
                     livery.dcsuf.date + " | Archive Size: " + livery.dcsuf.size + " \n" + livery.dcsuf.download,
                     title=Units.Units['aircraft'][livery.dcsuf.unit]['friendly'] + " - " + livery.dcsuf.title,
                     expand=False, highlight=True)

  def print_dcsuf_panel(self, livery):
    if livery:
      self.console.print(self._make_dcsuf_panel(livery))

  def setup_command_completer(self):
    completerDict = {}
    for k, v in self.commands.items():
      completerDict[k] = v['completer']
    self.completer = NestedCompleter.from_nested_dict(completerDict)

  def clear_and_print_header(self):
    clear_console()
    self.console.print(
           Rule(f'[bold gold1]DCS Livery Manager[/bold gold1] [bold sky_blue1]v{__version__}[/bold sky_blue1]',
           characters="~═~*", style="deep_pink2"))
    self.console.print('')

  def setup_console_window(self):
    self.console = Console(width=120, tab_size=4)
    #set_terminal_size(80, 50)

  def setup_livery_manager(self):
    self.console.print("DCSLM.exe Directory: \'" + os.getcwd() + "\'")
    self.lm = LiveryManager()
    lmData = self.lm.load_data()
    self.lm.make_dcslm_dirs()
    if not lmData:
      self.console.print("No existing \'DCSLM\\dcslm.json\' file found with config and livery data. Loading defaults.")
      self.prompt_livery_manager_defaults()
      self.lm.write_data()
    else:
      self.console.print("Loaded Livery Manager config and data from \'DCSLM\\dcslm.json\'")
      self.lm.LiveryData = lmData

  def prompt_livery_manager_defaults(self):
    if self.lm:
      self.console.print("\n\n[bold green underline]Mod Manager Mode:")
      self.console.print("If you use a mod manager, like \'OVGME\' or \'JSGME\', to manage your DCS mod installs, " +
                         "you can enable \'Mod Manager Mode\' to have it create a root directory named with the format " +
                         "[bold purple]{aircraft} - {livery title}[/bold purple].")
      self.console.print("\n[bold gold1]For \'Mod Manager Mode\' make sure you've placed \'DCSLM.exe\' inside your " +
                         "mod manager's directory that is " +
                         "configured for the [/bold gold1]\'DCS Saved Games\'[bold gold1] directory, " +
                         "not the DCS install directory.[/bold gold1]")
      ovgme = Confirm.ask("\n[bold]Do you want to enable Mod Manager Mode?[/bold]")
      self.lm.LiveryData['config']['ovgme'] = ovgme
      if ovgme:
        self.console.print("[green]Enabling Mod Manager mode.")

  def prompt_existing_livery(self, livery):
    if self.lm:
      self.console.print("\nThe livery \'" + livery.dcsuf.title + "\' is already installed and up to date.")
      return Confirm.ask("\n[bold]Do you still want to install the livery?[/bold]")
    return True

  def prompt_aircraft_livery_choice(self, livery, unitLiveries):
    choosenLiveries = []
    liveryChoices = ["[white]None[/white]"]
    for u in unitLiveries:
      if u in Units.Units['aircraft'].keys():
        liveryChoices.append("[white]" + Units.Units['aircraft'][u]['friendly'] + "[/white]")
      else:
        liveryChoices.append(u)
    liveryChoices.append("[bold white]All[/bold white]")
    if len(liveryChoices) > 3:
      choiceText = ""
      for i in range(0, len(liveryChoices)):
        choiceText += "[[sky_blue1]" + str(i) + "[/sky_blue1]]" + liveryChoices[i] + " "
      self.console.print("\nThere are multiple livery install locations for the [bold magenta]" +
                         Units.Units['aircraft'][livery.dcsuf.unit]['friendly'] + "[/bold magenta]. " +
                         "Please choose from one of the following choices by inputting the corresponding index number:")
      self.console.print("\n\t" + choiceText)
      try:
        choice = Prompt.ask("\n[bold]Which aircraft do you want the livery to be installed to?[/bold]",
                            choices=[str(i) for i in range(0,len(liveryChoices))])
      except KeyboardInterrupt:
        return []
      if choice == "0":
        return []
      elif choice == str(len(liveryChoices) - 1):
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
              try:
                if len(commandData['args']) or len(commandData['flags']):
                  commandData['exec'](sArgs=argList)
                else:
                  commandData['exec']()
              except Exception as e:
                self.console.print(e, style="bold red")
            if splitCommand[0] == "exit":
              runCommands = False
          else:
            self.console.print("Command \'" + splitCommand[0] + "\' not found.")
    self.console.print("Writing out current config and livery data to dcslm.json")
    self.lm.write_data()
    self.console.print("Exiting DCS Livery Manager.")

if __name__ == '__main__':
  os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))
  set_console_title(f'DCS Livery Manager v{__version__}')
  dcslmapp = DCSLMApp()
  dcslmapp.start()

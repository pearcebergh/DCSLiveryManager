import argparse
import glob
import os
import platform
import shutil
import sys
from datetime import datetime
from pprint import pprint
from patoolib.util import get_nt_7z_dir
from prompt_toolkit import PromptSession, HTML
from prompt_toolkit.completion import NestedCompleter
from rich import box
from rich.align import Align
from rich.console import Console, Group
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
from rich.text import Text
from rich.table import Table
from rich.theme import Theme
from DCSLM import __version__
from DCSLM.DCSUFParser import DCSUFParser, DCSUFPC
from DCSLM.Livery import Livery, DCSUserFile
from DCSLM.LiveryManager import LiveryManager
from DCSLM.UnitDefaults import UnitsOfficial
from DCSLM.UnitManager import UM
import DCSLM.Utilities as Utilities

# TODO: Add fallback upgrade path to find latest DCSLM.exe when unable to parse releases page
# TODO: add description.lua parts as optional field to unit config to auto-determine unit

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

class DCSLMApp:
  def __init__(self):
    self.console = None
    self.session = PromptSession(reserve_space_for_menu=6, complete_in_thread=True)
    self.completer = None
    self.completers = None
    self.commands = None
    self.lm = None
    self.parsedArgs = None
    self.theme = None

  def start(self):
    self.setup_commands()
    self.setup_rich_console_theme()
    self.setup_console_window()
    self.clear_and_print_header()
    self.parse_exe_args()
    self.setup_working_dir(self.parsedArgs.workingdir)
    self.setup_unit_manager()
    self.setup_livery_manager()
    self.setup_completers()
    self.quick_check_upgrade_available()
    self.check_7z_installed()
    self.check_last_update()
    self.print_motd()
    exeArgs = self.run_exe_args()
    if not exeArgs or self.parsedArgs.persist:
      self.run()
      exeArgs = False
    self.dcslm_exit(prompt=exeArgs)

  def setup_working_dir(self, workingDir=None):
    if workingDir:
      workingDir = str.replace(workingDir, "\"", '')
      workingDir = str.strip(workingDir) + "\\"
      workingDirName = os.path.dirname(os.path.join(workingDir))
      if os.path.isdir(workingDirName):
        os.chdir(workingDirName)
        self.console.print("Changing working directory to \'" + workingDir + "\'")
        return
    if not "PYCHARM_HOSTED" in os.environ:
      os.chdir(os.path.dirname(os.path.abspath(sys.executable)))  # Set working directory to executable directory

  def setup_commands(self):
    self.commands = {
      'install': {
        'usage': "\[id/url/path] \[id/url/path] \[id/url/path] ...",
        'desc': "Install DCS liveries from DCS User Files URLs/IDs or from an archive path",
        'flags': {
          'allunits': {
            'tags': ['-a', '--allunits'],
            'desc': "Do not prompt when given a choice to install to multiple units and install to all",
            'action': "store_true"
          },
          'keep': {
            'tags': ['-k', '--keep'],
            'desc': "Keep downloaded livery archive files",
            'action': "store_true"
          },
          'reinstall': {
            'tags': ['-r', '--reinstall'],
            'desc': "Do not prompt if the livery is already registered",
            'action': "store_true"
          },
          'screenshots': {
            'tags': ['-s', '--screenshots'],
            'desc': "Download and store the available screenshots of uploaded with the livery to the DCS User Files",
            'action': "store_true"
          },
          'unitselection': {
            'tags': ['-u', '--unitselection'],
            'desc': "Force selection of unit to install to",
            'action': "store_true"
          },
          'verbose': {
            'tags': ['-v', '--verbose'],
            'desc': "Verbose printing of livery install information for reference or debugging purposes",
            'action': "store_true"
          },
        },
        'args': {
          'path': {
            'type': "number/string",
            'optional': False,
            'desc': "DCS User Files URL/ID or Path",
            'variable': True,
            'skip': False
          },
        },
        'subcommands': {},
        'hidden': False,
        'exec': self.install_liveries
      },
      'uninstall': {
        'usage': "\[flags] livery1 livery2 livery3 ...",
        'desc': "Uninstall the given managed liveries from the \'ID\'",
        'flags': {
          'keep': {
            'tags': ['-k', '--keep'],
            'desc': "Keep livery files on disk but remove registry files (.dcslm.json)",
            'action': "store_true"
          },
        },
        'args': {
          'livery': {
            'type': "string",
            'optional': False,
            'desc': "Livery ID",
            'variable': True,
            'skip': False
          },
          'all': {
            'type': "string",
            'optional': True,
            'desc': "Uninstall all currently registered liveries",
            'variable': False,
            'skip': True
          },
        },
        'subcommands': {},
        'hidden': False,
        'exec': self.uninstall_liveries
      },
      'info': {
        'usage': "livery",
        'desc': "Get additional info about an installed livery",
        'flags': {},
        'args': {
          'livery': {
            'type': "string",
            'optional': False,
            'desc': "Livery ID",
            'variable': False,
            'skip': False
          },
        },
        'subcommands': {},
        'hidden': False,
        'exec': self.get_livery_info
      },
      'list': {
        'usage': "",
        'desc': "List currently installed liveries",
        'flags': {
          'ids': {
            'tags': ['ids'],
            'desc': "List the IDs of all registered liveries for copying",
            'action': "store_true"
          },
        },
        'args': {},
        'subcommands': {},
        'hidden': False,
        'exec': self.list_liveries
      },
      'check': {
        'usage': "",
        'desc': "Check for updates to any installed liveries from \'DCS User Files\'",
        'flags': {},
        'args': {},
        'subcommands': {},
        'hidden': False,
        'exec': self.check_liveries
      },
      'update': {
        'usage': "",
        'desc': "Update any installed liveries that have a more recent version uploaded to \'DCS User Files\'",
        'flags': {},
        'args': {},
        'subcommands': {},
        'hidden': False,
        'exec': self.update_liveries
      },
      'optimize': {
        'usage': "\[flags] livery",
        'desc': "Attempt to optimize an installed livery by looking for unused or shared files between liveries within packs",
        'flags': {
          'check': {
            'tags': ['-c', '--check'],
            'desc': "Check for possible optimizations and any errors with the livery",
            'action': "store_true"
          },
          'keepdesc': {
            'tags': ['-d','--keepdesc'],
            'desc': "Keep a copy of the original unmodified description.lua files",
            'action': "store_true"
          },
          'keepunused': {
            'tags': ['-u', '--keepunused'],
            'desc': "Keep unused files on disk at the end of optimization",
            'action': "store_true"
          },
          'reoptimize': {
            'tags': ['-r', '--reoptimize'],
            'desc': "Optimize liveries even if they have already been optimized",
            'action': "store_true"
          },
          'verbose': {
            'tags': ['-v', '--verbose'],
            'desc': "Verbose printing of livery file reference data for debugging purposes",
            'action': "store_true"
          },
        },
        'args': {
          'livery': {
            'type': "string",
            'optional': False,
            'desc': "Livery ID",
            'variable': True,
            'skip': False
          },
          'all': {
            'type': "string",
            'optional': True,
            'desc': "Attempt to optimize each currently registered livery",
            'variable': False,
            'skip': True
          },
        },
        'subcommands': {},
        'hidden': False,
        'exec': self.optimize_livery
      },
      'scan': {
        'usage': "",
        'desc': "Scan folders for existing liveries with .dcslm registry files",
        'flags': {
          'register': {
            'tags': ['-r', '--register'],
            'desc': "Prompt to register unknown liveries after scan",
            'action': "store_true"
          },
        },
        'args': {},
        'subcommands': {},
        'hidden': False,
        'exec': self.scan_for_liveries
      },
      'units': {
        'usage': "[flags] [unit]",
        'desc': "Display information about units and their configuration",
        'flags': {
          'export': {
            'tags': ['-e', '--export'],
            'desc': "Write the JSON config for a unit to disk",
            'action': "store_true"
          },
        },
        'args': {
          'unit': {
            'type': "string",
            'optional': True,
            'desc': "Display information about a specific unit",
            'variable': True,
            'skip': False
          },
        },
        'subcommands': {},
        'hidden': False,
        'exec': self.dcs_units
      },
      'config': {
        'usage': "[flags] [subcommand]",
        'desc': "Displays current DCSLM configuration settings",
        'flags': {
          'export': {
            'tags': ['-e', '--export'],
            'desc': "Write the JSON config file for some settings to allow for modification",
            'action': "store_true"
          },
          'reload': {
            'tags': ['-r', '--reload'],
            'desc': "Reload configuration file in to DCSLM",
            'action': "store_true"
          },
        },
        'args': {},
        'subcommands': {
          'dcsuf': {
            'desc': "DCS User Files Parsing configuration",
          },
          'lm': {
            'desc': "Livery Manager configuration",
          },
        },
        'hidden': False,
        'exec': self.dcslm_config
      },
      'upgrade': {
        'usage': "",
        'desc': "Upgrade DCSLM to the latest version",
        'flags': {},
        'args': {},
        'subcommands': {},
        'hidden': False,
        'exec': self.upgrade_dcslm
      },
      'help': {
        'usage': "",
        'desc': "List the commands and their usage",
        'flags': {},
        'args': {},
        'subcommands': {},
        'hidden': False,
        'exec': self.print_help
      },
      'exit': {
        'usage': "",
        'desc': "Exit the DCS Livery Manager program",
        'flags': {},
        'args': {},
        'subcommands': {},
        'hidden': False,
        'exec': None
      },
      'executable': {
        'usage': "DCSLM.exe \[flags] \[args]",
        'desc': "Command line arguments to be passed to the executable when launching",
        'flags': {
          'workingdir': {
            'tags': ['-w', '--workingdir'],
            'desc': "Set the working directory used as the root to create/read the [italic sky_blue1]DCSLM[/italic sky_blue1]" +
                    " directories and liveries",
            'action': "store"
          },
          'persist': {
            'tags': ['-p', '--persist'],
            'desc': "Keep the instance of DCS Livery Manager open after running executable arguments",
            'action': "store_true"
          },
          'update': {
            'tags': ['-d', '--update'],
            'desc': "Install any available updates to registered liveries",
            'action': "store_true"
          },
          'upgrade': {
            'tags': ['-g', '--upgrade'],
            'desc': "Upgrade DCS Livery Manager executable",
            'action': "store_true"
          },
        },
        'args': {
          '--install': {
            'type': "string",
            'optional': True,
            'desc': "Livery ID, URL, or path to the archive of the liveries you want to install",
            'variable': True,
            'skip': False
          },
          '--uninstall': {
            'type': "string",
            'optional': True,
            'desc': "Livery ID of the liveries you want to uninstall",
            'variable': True,
            'skip': False
          },
        },
        'subcommands': {},
        'hidden': True,
        'exec': None,
      }
    }

  def setup_completers(self):
    self.completers = {
      'commands': {
        'commands': [],
        'completer': None,
        'dict': {},
        'func': self.make_commands_completer
      },
      'units': {
        'commands': ['units'],
        'completer': None,
        'dict': {},
        'func': self.make_units_completer
      },
      'livery_ids': {
        'commands': ['uninstall', 'info', 'optimize'],
        'completer': None,
        'dict': {},
        'func': self.make_livery_ids_completer
      }
    }
    self._update_completers()
    self._make_nested_completers()

  def _update_completers(self):
    for k,v in self.completers.items():
      self._update_completer(v)

  def _update_completer_from_name(self, commandName):
    if commandName in self.completers.keys():
      self._update_completer(self.completers[commandName])

  def _update_completer(self, commandData):
    commandData['dict'] = commandData['func']()
    commandData['completer'] = NestedCompleter.from_nested_dict(commandData['dict'])

  def _make_nested_completer(self, command):
    commandDict = {}
    for k, d in self.completers.items():
      if command in d['commands']:
        commandDict = d['dict']
    return commandDict

  def _make_nested_completers(self):
    fullCompleterDict = self.completers['commands']['dict']
    for c in fullCompleterDict.keys():
      fullCompleterDict[c] = self._make_nested_completer(c)
    self.completer = NestedCompleter.from_nested_dict(fullCompleterDict)

  def _remove_brackets_sArgs(self, sArgs):
    correctedsArgs = []
    inBrackets = False
    for s in sArgs:
      containedBrackets = False
      if inBrackets:
        containedBrackets = True
      if s.startswith('['):
        inBrackets = True
      if s.endswith(']'):
        if inBrackets:
          containedBrackets = True
        inBrackets = False
      if not inBrackets and not containedBrackets:
        correctedsArgs.append(s)
    return correctedsArgs

  def _parse_command_args(self, command, sArgs):
    try:
      argsParser = argparse.ArgumentParser(usage=self.commands[command]['usage'],
                                           description=self.commands[command]['desc'],
                                           exit_on_error=False)
      for iF in self.commands[command]['flags'].keys():
        argsParser.add_argument(*self.commands[command]['flags'][iF]['tags'],
                                help=self.commands[command]['flags'][iF]['desc'],
                                action=self.commands[command]['flags'][iF]['action'], dest=iF)
      for iA in self.commands[command]['args'].keys():
        varArg = None
        if self.commands[command]['args'][iA]['skip']:
          continue
        if self.commands[command]['args'][iA]['variable']:
          if command == "executable":
            varArg = "*"
          else:
            varArg = "+"
        argsParser.add_argument(iA, type=str, help=self.commands[command]['args'][iA]['desc'], nargs=varArg)
      if len(self.commands[command]['subcommands'].keys()):
        subGroup = argsParser.add_mutually_exclusive_group(required=False)
        for iS in self.commands[command]['subcommands'].keys():
          subGroup.add_argument("--" + iS, help=self.commands[command]['subcommands'][iS]['desc'], action="store_true")
      parsedArgs = argsParser.parse_known_args(sArgs)
      if len(parsedArgs[1]):
        self.console.print("Failed to parse the following args for \'" + command + "\':", style="err")
        self.console.print("\t" + str(parsedArgs[1]), style="err")
      return parsedArgs[0]
    except SystemExit:
      raise RuntimeError("Unable to parse \'" + command + "\' command.")

  def _install_get_livery_unitdata(self, liveryStrData, reqSession, forceInstall):
    getUFStr = "Getting DCS User File information from " + liveryStrData['url']
    with self.console.status(liveryStrData['progress'] + getUFStr):
      livery = self.lm.get_livery_data_from_dcsuf_url(liveryStrData['url'], reqSession)
    if not livery or (livery and not livery.dcsuf):
      raise RuntimeError("Unable to get DCSUF info from livery \'" + liveryStrData['str'] + "\'")
    self.console.print(liveryStrData['progress'] + getUFStr + "\n")
    unitName = "Other"
    showDCSUFTags = True
    liveryUnitData = None
    if livery.dcsuf.unit != "Other" and livery.dcsuf.unit != "Vehicle":
      liveryUnitData = UM.get_unit_from_dcsuf_text(livery.dcsuf.unit)
      if liveryUnitData:
        unitName = livery.dcsuf.unit
        livery.dcsuf.unit = liveryUnitData
        showDCSUFTags = False
      else:
        unitName = "Unknown"
    self.print_dcsuf_panel(livery.dcsuf, unitName=unitName, showTags=showDCSUFTags)
    existingLivery = self.lm.get_registered_livery(id=int(liveryStrData['id']))
    if existingLivery and not forceInstall:
      if existingLivery.dcsuf.datetime == livery.dcsuf.datetime:
        if not self.prompt_existing_livery(existingLivery):
          raise RuntimeError("Skipping reinstalling livery.")
        else:
          liveryUnitData = existingLivery.dcsuf.unit
    return livery, liveryUnitData, unitName, showDCSUFTags

  def _install_select_unit(self, livery, liveryUnitData, manualUnitSelection, forceAllUnits):
    if livery.dcsuf.unit == "Other" or livery.dcsuf.unit == "Vehicle" or livery.dcsuf.unit == "Unknown"  or manualUnitSelection:
      liveryUnitData = self._install_prompt_unit(livery, manualUnitSelection)
    if not liveryUnitData:
      raise RuntimeError("Unable to find unit to install livery to.")
    else:
      livery.dcsuf.unit = liveryUnitData
    unitChoices = liveryUnitData.liveries
    if len(unitChoices) > 1 and not forceAllUnits:
      unitChoices = self.prompt_aircraft_livery_choice(livery, unitChoices)
    if len(unitChoices) == 0:
      raise RuntimeError("No units selected for install.")
    return unitChoices

  def _install_check_archive_path(self, livery, archiveName, progressStr, forceDownload):
    archivePath = self.lm.does_archive_exist(archiveName)
    liveryArchiveName = str(livery.dcsuf.id) + "_" + archiveName
    if not archivePath:
      archivePath = self.lm.does_archive_exist(liveryArchiveName)
    if archivePath:
      if not forceDownload and self.lm.compare_archive_sizes(archivePath, livery.dcsuf.download):
        self.console.print(progressStr + "\nArchive file \'" + livery.dcsuf.download.split('/')[-1] + "\' for \'" +
                           livery.dcsuf.title + "\' already exists. Using that instead.")
      else:
        archivePath = None
    return archivePath

  def _install_download_screenshots(self, livery, progressStr, session):
    if len(livery.dcsuf.screenshots):
      self.console.print("")
      with self.console.status(progressStr + "[bold]Downloading " + str(len(livery.dcsuf.screenshots)) +
                               " screenshots (--screenshots)..."):
        screenshotFiles = self.lm.download_screenshots(livery, session=session)
      self.console.print(progressStr + "Downloaded " + str(len(screenshotFiles)) + " screenshots.", style="bold")

  def _install_download_archive(self, livery, archivePath, progressStr, session, keepFiles):
    if not archivePath:
      downloadStr = "Downloading livery archive file "
      if keepFiles:
        downloadStr += "and saving (--keep) "
      downloadStr += livery.dcsuf.download
      self.console.print("\n" + progressStr + downloadStr)
      archivePath = self._download_archive_progress(livery, session=session)
    return archivePath

  def _install_copy_screenshots(self, livery, screenshotFiles, destinationPath, progressStr=""):
    copiedFolderPath = ""
    copiedScreenshots = []
    if len(screenshotFiles):
      with self.console.status(progressStr + "Copying screenshots to livery folder..."):
        firstLiveryName = list(livery.installs['liveries'].keys())[0]
        firstLivery = livery.installs['liveries'].get(firstLiveryName)
        destinationRoot = os.path.join(os.getcwd(), destinationPath, firstLivery['paths'][0])
        destinationFolder = os.path.join(destinationRoot, "screenshots")
        copiedFolderPath = destinationFolder
        if not os.path.isdir(destinationFolder):
          os.mkdir(destinationFolder)
        for s in screenshotFiles:
          if not len(s):
            continue
          destinationFilename = os.path.split(s)[-1]
          destinationFilepath = os.path.join(destinationFolder, destinationFilename)
          shutil.move(s, destinationFilepath)
          copiedScreenshots.append(destinationFilepath)
    return copiedFolderPath, copiedScreenshots

  def _install_archive_title_list(self, liveryStrData, detectedLiveries):
    possibleTitles = []
    splitPath = os.path.split(liveryStrData['path'])
    fileName = os.path.splitext(splitPath[1])[0]
    fileNameSpc = fileName.replace("_", " ")
    possibleTitles.append(fileNameSpc)
    for l in detectedLiveries:
      if not l['data']:
        possibleTitles.append(l['name'])
    return possibleTitles

  def _install_archive_create_livery(self, liveryStrData):
    livery = self.lm.get_livery_data_from_archive(liveryStrData['path'], liveryStrData['id'])
    return livery

  def _install_liveries(self, liveryStrings, keepFiles=False, forceDownload=False, forceInstall=False,
                        forceAllUnits=False, manualUnitSelection=False, verbose=False, screenshots=False):
    installData = {'success': [], 'failed': []}
    session = DCSUFParser().make_request_session()
    extractedID = None
    liveryIndex = 0
    for liveryStr in liveryStrings:
      liveryStrType = Utilities.determine_livery_string_location(liveryStr)
      liveryIndex += 1
      progressStr = "[" + str(liveryIndex) + "/" + str(len(liveryStrings)) + "] "
      liveryStrData = {'str': liveryStr, 'type': liveryStrType, 'progress': progressStr, 'id': None}
      if not liveryStrType:
        errorMsg = "Unable to determine livery string type from \'" + liveryStr + "\'."
        installData['failed'].append({'path': liveryStr, 'error': errorMsg})
        self.console.print(progressStr + errorMsg, style="err")
        continue
      elif liveryStrType == "DCSUF":
        correctedLiveryURL, urlID = Utilities.correct_dcs_user_files_url(liveryStr)
        liveryStrData['url'] = correctedLiveryURL
        liveryStrData['id'] = urlID
        if not correctedLiveryURL:
          errorMsg = "Failed to get DCS User Files url or ID from \'" + liveryStr + "\'."
          installData['failed'].append({'path': liveryStr, 'error': errorMsg})
          self.console.print(progressStr + errorMsg, style="err")
          continue
      elif liveryStrType == "Archive":
        liveryStrData['path'] = os.path.normpath(liveryStr)
        liveryStrData['id'] = self.lm.get_next_local_livery_id()
      livery = None
      try:
        extractedID = liveryStrData['id']
        screenshotFiles = []
        if liveryStrData['type'] == 'DCSUF':
          livery, liveryUnitData, unitName, dcsufTags = self._install_get_livery_unitdata(liveryStrData, session, forceInstall)
          unitChoices = self._install_select_unit(livery, liveryUnitData, manualUnitSelection, forceAllUnits)
          livery.installs['units'] = unitChoices
          livery.ovgme = livery.generate_ovgme_folder()
          archiveName = livery.dcsuf.download.split('/')[-1]
          archivePath = self._install_check_archive_path(livery, archiveName, progressStr, forceDownload)
          if screenshots:
            screenshotFiles = self._install_download_screenshots(livery, progressStr)
          archivePath = self._install_download_archive(livery, archivePath, progressStr, session, keepFiles)
        else:
          archivePath = liveryStrData['path']
          livery = self._install_archive_create_livery(liveryStrData)
          unitChoices = []
        if archivePath:
          livery.archive = archivePath
          self.lm.remove_extracted_livery_archive(livery, extractedID=extractedID)
          self.console.print("\n" + progressStr + "[bold]Running extraction program on downloaded archive:")
          extractPath = self.lm.extract_livery_archive(livery, verbose=verbose)
          if extractPath:
            self.console.print("\n" + progressStr + "Extracted \'" + livery.archive + "\' to temporary directory.")
            destinationPath = self.lm.generate_livery_destination_path(livery)
            livery.destination = destinationPath
            self.console.print(progressStr + "Detecting extracted liveries...")
            extractedLiveryFiles = self.lm.get_extracted_livery_files(livery, extractPath)
            detectedLiveries = self.lm.detect_extracted_liveries(livery, extractPath, extractedLiveryFiles)
            if liveryStrData['type'] == 'Archive':
              titlesList = self._install_archive_title_list(liveryStrData, detectedLiveries)
              filledDCSUF, usedDCSUF = self.prompt_dcsuf_info(titlesList, livery=livery)
              if filledDCSUF:
                if not usedDCSUF:
                  filledDCSUF.id = livery.dcsuf.id
                  filledDCSUF.size = livery.dcsuf.size
                  filledDCSUF.date = livery.dcsuf.date
                  filledDCSUF.datetime = livery.dcsuf.datetime
                  filledDCSUF.download = livery.dcsuf.download
                livery.dcsuf = filledDCSUF
                liveryUnitData = livery.dcsuf.unit
                unitChoices = self._install_select_unit(livery, liveryUnitData, manualUnitSelection, forceAllUnits)
                livery.installs['units'] = unitChoices
            installRoots = self.lm.generate_aircraft_livery_install_path(livery, unitChoices)
            if len(detectedLiveries) and len(installRoots):
              liveryNames = [l['name'] for l in detectedLiveries if not l['data']]
              self.console.print(liveryNames)
              self.console.print(progressStr + "Generating livery install paths...")
              installPaths = self.lm.generate_livery_install_paths(livery, installRoots, detectedLiveries)
              if len(installPaths):
                self.console.print(progressStr + "Installing " + str(len(detectedLiveries)) +
                                   (" liveries" if len(detectedLiveries) > 1 else " livery") + " to " +
                                   str(len(installRoots)) + " aircraft.")
                with self.console.status(progressStr + "Installing extracted liveries..."):
                  copiedLiveries = self.lm.copy_detected_liveries(livery, extractPath,
                                                                  extractedLiveryFiles, installPaths)
                if len(copiedLiveries):
                  if screenshots:
                    copiedFolderPath, copiedScreenshots = self._install_copy_screenshots(livery, screenshotFiles,
                                                                                         destinationPath, progressStr)
                    if len(copiedScreenshots):
                      self.console.print(progressStr + "Downloaded " + str(len(copiedScreenshots)) +
                                         " screenshots to \'" + copiedFolderPath + "\'")
                  with self.console.status(progressStr + "Writing registry files..."):
                    self.lm.write_livery_registry_files(livery)
                  self.console.print(progressStr + "Wrote " + str(len(installRoots) * len(detectedLiveries)) +
                                     " registry files to installed livery directories.")
                  self.lm.register_livery(livery)
                  self.console.print("[bold green]Livery[/bold green] \'" + str(livery.dcsuf.title) +
                                     "\' [bold green]registered with ID[/bold green] " + str(livery.dcsuf.id) + "[bold green]!")
                  livery.calculate_size_installed_liveries()
                  installData['success'].append(livery)
                else:
                  raise RuntimeError(progressStr + "Failed to copy livery files to install directories!")
              else:
                raise RuntimeError(progressStr + "Failed to generate install paths!")
            else:
              raise RuntimeError(progressStr + "Failed to detect valid livery directories from extracted livery archive!")
          else:
            raise RuntimeError(progressStr + "Failed to extract livery archive \'" + livery.archive + "\'.")
      except KeyboardInterrupt as e:
        installData['failed'].append({'path': liveryStr, 'error': e})
        self.console.print("Install exception: keyboard interrupt", style="err")
      except Exception as e:
        installData['failed'].append({'path': liveryStr, 'error': e})
        self.console.print(e, style="err")
      finally:
        if livery:
          if livery.destination:
            self.console.print(progressStr + "Removing temporarily extracted folder.")
            if not self.lm.remove_extracted_livery_archive(livery, extractedID=extractedID):
              failedExtractPath = os.path.join(os.getcwd(), self.lm.FolderRoot, "extract", str(livery.dcsuf.id))
              failedMsg = "Failed to remove all extracted files to directory " + failedExtractPath
              self.console.print(progressStr + failedMsg, style="red")
              installData['failed'].append({'path': livery.dcsuf.id, 'error': failedMsg})
          if livery.archive and not keepFiles and liveryStrType == "DCSUF":
            self.console.print(progressStr + "Removing downloaded archive file \'" + os.path.split(livery.archive)[1] + "\'.")
            self.lm.remove_downloaded_archive(livery, livery.archive)
          if screenshots:
            self.console.print(progressStr + "Removing temporarily created screenshots folder")
            screenshotsFolder = os.path.join(os.getcwd(), self.lm.FolderRoot, "screenshots", str(livery.dcsuf.id))
            if os.path.isdir(screenshotsFolder):
              if Utilities.validate_remove_path(screenshotsFolder):
                shutil.rmtree(screenshotsFolder, onerror=Utilities.remove_readonly)
          self.console.print("")
    return installData

  def _install_prompt_unit_input(self):
    inputStr = self.session.prompt(HTML("<b>Enter unit name:</b> "),
                                   completer=self.completers['units']['completer'])
    inputStr = str.strip(inputStr)
    if inputStr == "units":
      self.dcs_units(sArgs="")
      return None
    inputUnit = UM.get_unit_from_friendly_name(inputStr)
    if not inputUnit:
      self.console.print("[red]No matching unit found from input \'" + inputStr + "\'.")
      inputUnit = None
    return inputUnit

  def _install_prompt_unit(self, livery, manualUnitSelection=False):
    selectedUnit = None
    if len(livery.dcsuf.tags) and not manualUnitSelection:
      matchedUnits = UM.get_units_from_tags(livery.dcsuf.tags)
      if not len(matchedUnits):
        tagsStr = ", ".join(livery.dcsuf.tags)
        self.console.print("[red]Unable to find matching unit from tags: " + tagsStr)
      else:
        try:
          if len(matchedUnits) > 1:
            choicesList = [str(i) for i in range(len(matchedUnits) + 1)]
            choicesStr = "\t[[sky_blue1]0[/sky_blue1]][white]None[/white] "
            for i in range(0, len(matchedUnits)):
              choicesStr += "[[sky_blue1]" + str(i + 1) + "[/sky_blue1]]" + matchedUnits[i].friendly + " "
            self.console.print("\nMultiple units matched. Select from one of the following to set as the unit by " +
                               "inputting the corresponding index number:\n")
            self.console.print(choicesStr)
            self.console.print("")
            selectedChoice = Prompt.ask("What unit do you want to select?", choices=choicesList)
            if selectedChoice != "0":
              selectedInt = int(selectedChoice) - 1
              if selectedInt < len(matchedUnits):
                selectedUnit = matchedUnits[selectedInt]
          else:
            selectedUnit = matchedUnits[0]
            self.console.print("Matched unit tags with unit \'" + selectedUnit.friendly + "\'.")
        except KeyboardInterrupt:
          return None
    if not selectedUnit:
      self.console.print("\n[red]No units selected or matched. Type in the name of the unit you want to install to, " +
                         "or [magenta]'none'[/magenta] to skip.[/red]")
      self.console.print("[red]You can also type [bold green]'units'[/bold green] to see a list of currently " +
                         "registered units.[/red]\n")
      try:
        while True:
          inputStr = self.session.prompt(HTML("<b>Enter unit name:</b> "),
                                         completer=self.completers['units']['completer'])
          inputStr = str.strip(inputStr)
          if inputStr == "units":
            self.dcs_units(sArgs="")
            continue
          elif inputStr == "none":
            break
          inputUnit = UM.get_unit_from_friendly_name(inputStr)
          if not inputUnit:
            self.console.print("[red]No matching unit found from input \'" + inputStr + "\'.")
          else:
            selectedUnit = inputUnit
            break
      except KeyboardInterrupt:
        return None
    if selectedUnit:
      self.console.print("Selected unit \'" + selectedUnit.friendly + "\' to install to.")
    return selectedUnit

  def _print_livery_install_report(self, installData, tableTitle):
    if len(installData['success']):
      installTable = Table(title=tableTitle, expand=False, box=box.ROUNDED)
      installTable.add_column("Unit", justify="left", no_wrap=True, style="green")
      installTable.add_column("ID", justify="center", no_wrap=True, style="sky_blue1")
      installTable.add_column("Livery Title", justify="center", style="")
      installTable.add_column("# Liveries", justify="center", no_wrap=True, style="magenta")
      installTable.add_column("Size (MB)", justify="right", no_wrap=True, style="bold gold1")
      for l in installData['success']:
        unitData = l.dcsuf.unit
        if unitData:
          installTable.add_row(unitData.friendly, str(l.dcsuf.id), l.dcsuf.title, str(l.get_num_liveries()),
                               Utilities.bytes_to_mb_string(l.get_size_installed_liveries()))
      self.console.print(installTable)
    if len(installData['failed']):
      self.console.print("[err]Failed Livery Installs:")
      for l in installData['failed']:
        self.console.print("[err]" + l['path'] + "[/err][red]: " + str(l['error']))

  def _install_correct_parsed_arg_paths(self, parsedPaths):
    fixedPaths = []
    openQuotes = False
    openIndex = 0
    for i in range(0, len(parsedPaths)):
      p = parsedPaths[i]
      if p[0] == "\"" or p[0] == "\'":
        if not openQuotes:
          openQuotes = True
          openIndex = i
      if openQuotes:
        if p[-1] == "\"" or p[-1] == "\'":
          openQuotes = False
          combinedPath = ' '.join(parsedPaths[openIndex:i+1])
          fixedPaths.append(combinedPath[1:-1])
      else:
        fixedPaths.append(p)
    return fixedPaths

  def install_liveries(self, sArgs):
    installArgs = self._parse_command_args("install", sArgs)
    installArgs.path = self._install_correct_parsed_arg_paths(installArgs.path)
    self.reload_dcslm_config()
    self.console.print("Attempting to install " + str(len(installArgs.path)) +
                       (" liveries" if len(installArgs.path) != 1 else " livery") + ".")
    installData = self._install_liveries(installArgs.path, keepFiles=installArgs.keep,
                                         forceInstall=installArgs.reinstall, forceAllUnits=installArgs.allunits,
                                         manualUnitSelection=installArgs.unitselection, verbose=installArgs.verbose,
                                         screenshots=installArgs.screenshots)
    self.lm.write_data()
    self.completers['livery_ids']['dict'] = self.make_livery_ids_completer()
    self._update_completer_from_name('livery_ids')
    self._make_nested_completers()
    self._print_livery_install_report(installData, "Livery Install Report")

  def uninstall_liveries(self, sArgs):
    sArgs = self._remove_brackets_sArgs(sArgs)
    uninstallArgs = self._parse_command_args("uninstall", sArgs)
    self.reload_dcslm_config()
    uninstallData = {'success': [], 'failed': []}
    uninstallLiveries = uninstallArgs.livery
    if len(uninstallArgs.livery) and str.lower(uninstallArgs.livery[0]) == "all":
      confirmAll = Confirm.ask("Do you want to uninstall all [bright_cyan]" + str(self.lm.get_num_registered_liveries()) +
                               "[/bright_cyan] registered liveries?", console=self.console)
      if confirmAll:
        uninstallLiveries = list(self.lm.get_registered_livery_ids())
      else:
        return
    if not len(uninstallLiveries):
      self.console.print("No liveries given to \'uninstall\' command.")
      return
    self.console.print("Attempting to uninstall " + str(len(uninstallLiveries)) +
                       (" registered liveries" if len(uninstallLiveries) > 1 else " registered livery") + ".")
    liveryIndex = 0
    for liveryStr in uninstallLiveries:
      liveryIndex += 1
      progressStr = "[" + str(liveryIndex) + "/" + str(len(uninstallLiveries)) + "] "
      if str.isnumeric(liveryStr):
        try:
          self.console.print(progressStr + "Uninstalling \'" + liveryStr + "\'.")
          livery = self.lm.get_registered_livery(id=int(liveryStr))
          if livery:
            self.console.print(progressStr + "Found registered livery.")
            numLiveries = str(livery.get_num_liveries())
            uninstallStatus = "Removing " + numLiveries + " installed livery directories..."
            if uninstallArgs.keep:
              uninstallStatus = "Removing " + numLiveries + " livery registry files... (--keep)"
            with self.console.status(progressStr + uninstallStatus):
              self.lm.uninstall_livery(livery, keepFiles=uninstallArgs.keep)
            if uninstallArgs.keep:
              self.console.print(progressStr + "Removed " + numLiveries + " livery registry files. (--keep)")
            else:
              self.console.print(progressStr + "Removed " + numLiveries + " installed livery directories.")
            uninstallData['success'].append(livery)
            self.console.print(progressStr + "Successfully uninstalled livery \'" + livery.dcsuf.title + "\'.")
          else:
            raise RuntimeError(progressStr + "Livery \'" + liveryStr + "\' not found in livery registry.")
        except Exception as e:
          uninstallData['failed'].append({'livery': liveryStr, 'error': e})
          self.console.print(e, style="err")
        finally:
          self.console.print("")
    if len(uninstallData['success']):
      self.console.print("[bold green]Successful Livery Uninstalls:")
      for l in uninstallData['success']:
        self.console.print("\t(" + str(l.dcsuf.id) + ") " + l.dcsuf.title, highlight=False)
      self.lm.write_data()
      self.completers['livery_ids']['dict'] = self.make_livery_ids_completer()
      self._make_nested_completers()
    if len(uninstallData['failed']):
      self.console.print("[err]Failed Livery Uninstalls:")
      for l in uninstallData['failed']:
        self.console.print("\t" + l['livery'] + "[red]: " + str(l['error']))

  def _check_all_liveries_updates(self, verbose=False):
    liveryStatus = []
    checkProgress = Progress("[progress.description]{task.description}",
                             SpinnerColumn(spinner_name="dots"),
                             BarColumn(),
                             "{task.completed}/{task.total}",
                             console=self.console)
    checkTask = checkProgress.add_task("Checking liveries for updates", total=len(self.lm.Liveries.keys()))
    with checkProgress:
      session = DCSUFParser().make_request_session()
      for l in self.lm.Liveries.values():
        if l.dcsuf.id <= self.lm.IDLocalMax:
          liveryStatus.append({'livery': l, 'update': False, 'skipped': True})
          continue
        reqDCSUF = DCSUFParser().get_dcsuserfile_from_url(str(l.dcsuf.id), session)
        if reqDCSUF:
          if l.dcsuf.datetime < reqDCSUF.datetime:
            liveryStatus.append({'livery': l, 'update': True, 'skipped': False})
            if verbose:
              checkProgress.print("Found update for livery \'" + l.dcsuf.title + "\'!")
          else:
            liveryStatus.append({'livery': l, 'update': False, 'skipped': False})
        else:
          liveryStatus.append({'livery': l, 'update': False, 'skipped': False, 'failed': "Failed to parse HTML"})
        checkProgress.update(checkTask, advance=1)
    return liveryStatus

  def check_liveries(self):
    if not len(self.lm.Liveries.keys()):
      self.console.print("[red]No liveries registered to check.")
      return
    liveryStatus = self._check_all_liveries_updates()
    statusTable = Table(title="Livery Update Status", expand=False, box=box.ROUNDED)
    statusTable.add_column("Livery ID", justify="center", no_wrap=True, width=10, style="bright_cyan")
    statusTable.add_column("Livery Title", justify="center", no_wrap=True)
    statusTable.add_column("Status", justify="center", no_wrap=True)
    numToUpdate = 0
    for l in liveryStatus:
      if l['update']:
        statusTable.add_row(str(l['livery'].dcsuf.id), l['livery'].dcsuf.title, "[red]Out of date")
        numToUpdate += 1
      elif 'failed' in l.keys():
        statusTable.add_row(str(l['livery'].dcsuf.id), l['livery'].dcsuf.title, "[err]" + l['failed'])
      elif l['skipped']:
        statusTable.add_row(str(l['livery'].dcsuf.id), l['livery'].dcsuf.title, "[red]Skipped")
      else:
        statusTable.add_row(str(l['livery'].dcsuf.id), l['livery'].dcsuf.title, "[green]Up to date")
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
      self.set_last_update()
      self.lm.write_data()
      return
    self.console.print("Found " + str(len(updateList)) + " liveries that need updating.")
    self.console.print("")
    updateData = self._install_liveries(updateList, forceDownload=True)
    self.set_last_update()
    self.lm.write_data()
    self.completers['livery_ids']['completer'] = self.make_livery_ids_completer()
    self.completers['livery_ids']['dict'] = NestedCompleter.from_nested_dict(self.completers['livery_ids']['completer'])
    self._make_nested_completers()
    self._print_livery_install_report(updateData, "Livery Update Report")

  def list_liveries(self, sArgs):
    def sort_list_by_unit_then_title(e):
      return e[0] + " - " + e[1]

    sArgs = self._remove_brackets_sArgs(sArgs)
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
      unitData = l.dcsuf.unit
      if unitData:
        friendlyUnit = unitData.friendly
      else:
        friendlyUnit = l.dcsuf.unit
      unitStr = friendlyUnit
      if len(l.installs['units']) > 1:
        unitStr += "[bold gold1]+" + str(len(l.installs['units']) - 1) + "[/bold gold1]"
      liverySizeMB = Utilities.bytes_to_mb(l.get_size_installed_liveries())
      footerData['size'] += liverySizeMB
      footerData['registered'] += 1
      footerData['installed'] += l.get_num_liveries()
      unitName = l.dcsuf.unit
      if l.dcsuf.unit.generic not in footerData['units']:
        footerData['units'].append(l.dcsuf.unit.generic)
      sizeStr = Utilities.mb_to_mb_string(liverySizeMB)
      if l.is_optimized():
        sizeStr = "[size.opt]" + sizeStr + "[/size.opt]"
      liveryRows.append((unitStr, str(l.dcsuf.id), l.dcsuf.title, sizeStr))
      if len(unitStr) > len(longestUnit):
        longestUnit = unitStr
    footerString = "[num]" + str(footerData['registered']) + "[/num] Registered Liveries    "
    footerString += "[num]" + str(footerData['installed']) + "[/num] Installed Livery Directories    "
    footerString += "[num]" + str(len(footerData['units'])) + "[/num] Units    "
    footerString += "[size]" + Utilities.mb_to_mb_string(footerData['size']) + "[/size] MB Total Size"
    unitColWidth = max(8, min(13, len(longestUnit)))
    statusTable = Table(title="List of Registered Liveries", expand=False, box=box.ROUNDED, highlight=False,
                        caption=footerString, caption_justify="center")
    statusTable.add_column("Unit", justify="center", no_wrap=True, style="unit", min_width=unitColWidth)
    statusTable.add_column("ID", justify="center", no_wrap=True, style="sky_blue1", width=9)
    statusTable.add_column("Livery Title", justify="center", no_wrap=True, overflow='ellipsis', max_width=72)
    statusTable.add_column("Size (MB)", justify="right", no_wrap=True, style="size", width=10)
    liveryRows.sort(key=sort_list_by_unit_then_title)
    for i in range(0, len(liveryRows)):
      l = liveryRows[i]
      isEndSection = False
      if i != len(liveryRows) - 1:
        nextUnit = liveryRows[i + 1][0]
        currentUnit = l[0]
        if nextUnit != currentUnit:
          isEndSection = True
          if len(nextUnit) > len(currentUnit) and nextUnit[:len(currentUnit)] == currentUnit:
            isEndSection = False
          elif len(currentUnit) > len(nextUnit) and currentUnit[:len(nextUnit)] == nextUnit:
            isEndSection = False
      if i == len(liveryRows) - 1: # for footer
        isEndSection = True
      statusTable.add_row(*l, end_section=isEndSection)
    self.console.print(statusTable)

  def _make_livery_rendergroup(self, livery):
    liveryTable = Table.grid(expand=True, padding=(0,2,2,0))
    liveryTable.add_column("Info", justify="right", no_wrap=True, style="sky_blue1")
    liveryTable.add_column("Content", justify="left")
    archiveStyle = "[red]"
    if os.path.isfile(livery.archive):
      archiveStyle = "[green]"
    liveryTable.add_row("Archive", archiveStyle + livery.archive)
    if self.lm.LiveryData['config']['ovgme']:
      liveryTable.add_row("Mod Managed Directory", livery.ovgme)
    liveryTable.add_row("Destination", livery.destination)
    liveryTable.add_row("Units", Text("[" + ', '.join(livery.installs['units']) + "]"))
    liveryTable.add_row("Liveries", Text("[" + ', '.join(livery.installs['liveries'].keys()) + "]"))
    installs = []
    for l,i in livery.installs['liveries'].items():
      installs.extend(i['paths'])
    liveryTable.add_row("Paths", Text(str(installs)))
    liveryRG = liveryTable
    return liveryRG

  def get_livery_info(self, sArgs):
    sArgs = self._remove_brackets_sArgs(sArgs)
    livery = None
    if len(sArgs) == 1:
      liveryID = sArgs[0]
      livery = self.lm.get_registered_livery(id=liveryID)
    else:
      for s in sArgs:
        if s.isdecimal():
          livery = self.lm.get_registered_livery(id=s)
          if livery:
            break
    if livery:
      dcsufPanel = self._make_dcsuf_panel(livery.dcsuf, childPanel=True)
      dcsufPanel.title = "[magenta]DCS User Files Information"
      dcsufPanel.title_align = "left"
      dcsufAlign = Align(dcsufPanel, align="center")
      liveryRG = self._make_livery_rendergroup(livery)
      liveryAlign = Align(liveryRG, align="center")
      liveryInfoPanelGroup = Group(dcsufAlign, liveryAlign)
      panelTitle = "[sky_blue1]" + livery.dcsuf.title + "[/sky_blue1] [green]Livery Info"
      self.console.print(Panel(liveryInfoPanelGroup, title=panelTitle, highlight=True, expand=False))
    else:
      self.console.print("[red]Unable to find installed livery from \'" + ' '.join(sArgs) + "\'.")

  def _scan_register_unknown_liveries_register(self, liveryData):
    l = Livery()
    titleOptions = []
    selectedUnit = None
    for u in liveryData.keys():
      l.installs['units'].append(u)
      for ld in liveryData[u]:
        ld['livery'] = l
        if not selectedUnit:
          selectedUnit = ld['unit']
        titleOptions.append(ld['title'])
        liverySize = Utilities.get_size_of_directory(ld['path'])
        nl = { 'size': liverySize, 'paths': [ld['path'][11:-1]]}
        if not ld['title'] in l.installs['liveries'].keys():
          l.installs['liveries'][ld['title']] = nl
        else:
          l.installs['liveries'][ld['title']]['paths'].extend(nl['paths'])
    l.destination = self.lm.generate_livery_destination_path(l)
    l.archive = ""
    liveryInfo, dcsufInfo = self.prompt_dcsuf_info(titles=titleOptions, unit=selectedUnit)
    l.dcsuf = liveryInfo
    l.ovgme = l.generate_ovgme_folder()
    return l

  def _scan_register_unknown_liveries(self, unknownPaths):
    scanReport = {'success': {}, 'failed':[]}
    unitLiveryPairs = []
    for p in unknownPaths:
      splitPath = p.split("\\")
      if not splitPath or len(splitPath) < 4:
        scanReport['failed'].append({'path': p, 'error': "Invalid path"})
        continue
      unitPath = splitPath[-3]
      liveryPath = splitPath[-2]
      unit = UM.get_unit_from_liveries_dir(unitPath)
      if not unit:
        scanReport['failed'].append({'path': p, 'error': "Unit root folder not found in configured units"})
        continue
      unitLiveryPairs.append({'path': p, 'title': liveryPath, 'unit': unit, 'unitPath': unitPath})
    if len(unitLiveryPairs):
      registerLiveries = True
      self.console.print("Matched " + str(len(unitLiveryPairs)) + " livery unit roots with configured units.")
      while registerLiveries:
        self.console.print("\nUnknown liveries to register:")
        for i in range(0, len(unitLiveryPairs)):
          u = unitLiveryPairs[i]
          self.console.print("\t[" + str(i + 1) + "] [unit]" + u['unit'].friendly + "[/unit] - " + u['title'])
        self.console.print("\t[0] [unit] None")
        self.console.print("\nSelect which liveries to register. Enter multiple numbers to register a livery pack.")
        selectingLiveries = True
        selectedLiveries = {}
        while selectingLiveries:
          choiceInput = Prompt.ask("[bold]Liveries to Register[/bold]", console=self.console)
          selectedIndices = []
          if len(choiceInput):
            choices = choiceInput.split(' ')
            for i in range(0, len(choices)):
              if choices[i].isnumeric():
                pairIndex = int(choices[i])
                if pairIndex > 0 and pairIndex <= len(unitLiveryPairs):
                  c = unitLiveryPairs[pairIndex - 1]
                  if c['unitPath'] not in selectedLiveries.keys():
                    selectedLiveries[c['unitPath']] = []
                  selectedLiveries[c['unitPath']].append(c)
                  selectedIndices.append(pairIndex)
                elif pairIndex == 0 and len(choices) == 1:
                  selectingLiveries = False
                  registerLiveries = False
                  break
            if not selectingLiveries: # Selected none
              break
            # Register Liveries
            if len(selectedLiveries):
              selectingLiveries = False
              nL = self._scan_register_unknown_liveries_register(selectedLiveries)
              if nL:
                self.lm.register_livery(nL)
                self.console.print("[bold green]Livery[/bold green] \'" + str(nL.dcsuf.title) +
                                   "\' [bold green]registered with ID[/bold green] " + str(nL.dcsuf.id) + "[bold green]!")
                self.lm.write_livery_registry_files(nL)
                self.console.print("Wrote " + str(len(nL.installs['units']) * nL.get_num_liveries()) +
                                   " registry files to installed livery directories.")
                scanReport['success'][nL.dcsuf.id] = nL
              else:
                titleString = ""
                for u in selectedLiveries.keys():
                  for sL in selectedLiveries[u]:
                    titleString += sL['title'] + "/"
                self.console.print("[err]Unable to create and register livery[/err] \'" + titleString[:-1] + "\'")
                scanReport['failed'].append(titleString[:-1])
            # Remove from list of unknown liveries
            for u in selectedLiveries.keys():
              for sL in selectedLiveries[u]:
                if 'livery' in sL.keys():
                  if sL['livery']:
                    if sL in unitLiveryPairs:
                      unitLiveryPairs.remove(sL)
        if len(unitLiveryPairs) == 0:
          registerLiveries = False
    return scanReport

  def scan_for_liveries(self, sArgs):
    scanArgs = self._parse_command_args("scan", sArgs)
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
          unit = UM.get_unit_from_liveries_dir(unitName)
          if unit:
            unitFolders.append(uD)
    self.console.print("Matched " + str(len(unitFolders)) + " known unit directories.")
    installedDCSLMFiles = []
    unknownLiveries = []
    for uF in unitFolders:
      livDirs = glob.glob(uF + "/*/")
      for lD in livDirs:
        regFiles = glob.glob(lD + ".dcslm*")
        if regFiles:
          installedDCSLMFiles.append(regFiles[0])
        else:
          unknownLiveries.append(lD)
    self.console.print("Found " + str(len(installedDCSLMFiles)) + " \'.dcslm\' registry files.")
    unknownStr = "Found [red]" + str(len(unknownLiveries)) + "[/red] unknown livery directories."
    if not scanArgs.register:
      unknownStr += " (Use --register to add local liveries to [exe]DCSLM[/exe])"
    self.console.print(unknownStr)
    registeredLiveries = {'success':{}, 'failed':[], 'existing':{}}
    if scanArgs.register and len(unknownLiveries):
      scanRegisterReport = self._scan_register_unknown_liveries(unknownLiveries)
      registeredLiveries['success'] = scanRegisterReport['success']
      registeredLiveries['failed'] = scanRegisterReport['failed']
    with self.console.status("Checking liveries against registry..."):
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
      reportStr += "Registered " + str(len(registeredLiveries['success'])) + " liveries. "
      self.completers['livery_ids']['dict'] = self.make_livery_ids_completer()
      self._make_nested_completers()
    if len(registeredLiveries['existing']):
      reportStr += "Matched " + str(len(registeredLiveries['existing'])) + " existing registered liveries. "
    if len(registeredLiveries['failed']):
      reportStr += "Failed to register " + str(len(registeredLiveries['failed'])) + " liveries from \'.dcslm\' files:[err]\n"
      reportStr += ', '.join(registeredLiveries['failed'])
    self.lm.write_data()
    self.console.print(reportStr)

  def quick_check_upgrade_available(self):
    relData = self.request_upgrade_information()
    if relData:
      if len(relData):
        self.console.print("\nYour DCSLM [err]v" + str(__version__) + "[/err] is out of date!\n" +
                           "Use the \'upgrade\' command to upgrade [exe]DCSLM[/exe] to [bold green]v" +
                           relData[0]['version'] + "[/bold green]")

  def request_latest_upgrade_download(self):
    import requests
    import pkg_resources
    from bs4 import BeautifulSoup
    # Get all links and find released exe downloads
    try:
      releaseData = []
      rData = {
        'name': "",
        'version': "",
        'desc': "N/A",
        'date': "N/A",
        'download': ""
      }
      relReq = requests.get("https://github.com/pearcebergh/DCSLiveryManager/releases", timeout=5)
      relHTML = BeautifulSoup(relReq.text, 'html.parser')
      rootPath = "/pearcebergh/DCSLiveryManager/releases/download/"
      releaseLinks = []
      for href in relHTML.find_all('a', href=True):
        hrefStr = str(href.get('href'))
        if rootPath in hrefStr:
          releaseLinks.append(hrefStr)
      highestTag = "0.0.0"
      parsedHighest = pkg_resources.parse_version(highestTag)
      for rL in releaseLinks:
        splitRL = rL.split("/")
        if pkg_resources.parse_version(splitRL[5]) > parsedHighest:
          highestTag = splitRL[5]
          parsedHighest = pkg_resources.parse_version(splitRL[5])
      if highestTag != "0.0.0":
        rData['name'] = highestTag + " Release"
        rData['version'] = highestTag
        rData['download'] = "https://github.com" + rootPath + highestTag + "/DCSLM.exe"
        releaseData.append(rData)
      pprint(releaseData)
      return releaseData
    except Exception as e:
      self.console.print("Failed to parse GitHub release page for upgrade information.", style="err")
      return None

  def request_upgrade_information(self):
    import requests
    import pkg_resources
    from datetime import datetime
    from bs4 import BeautifulSoup
    try:
      releaseData = []
      relReq = requests.get("https://github.com/pearcebergh/DCSLiveryManager/releases", timeout=5)
      relHTML = BeautifulSoup(relReq.text, 'html.parser')
      relDivs = relHTML.find_all('div', {'class': "d-flex flex-column flex-md-row my-5 flex-justify-center"})
      for r in relDivs:
        rData = {
          'name': r.find('a', {'class': "Link--primary"}).text,
          'version': r.find('span', {'class': "ml-1 wb-break-all"}).text.strip(),
          'desc': r.find('div', {'class': "markdown-body my-3"}).text,
          'date': "",
          'download': ""
        }
        dateCls = r.find('relative-time', {'class': "no-wrap"})
        if not dateCls:
          dateCls = r.find('local-time', {'class': "no-wrap"})
        if dateCls:
          dateDT = dateCls.get('datetime')
          if dateDT:
            dtRelease = datetime.strptime(dateDT, "%Y-%m-%dT%H:%M:%SZ")
            dtStr = dtRelease.strftime("%b %d, %Y")
            rData['date'] = dtStr
        for a in r.find_all('a'):
          if a.text.strip() == "DCSLM.exe":
            rData['download'] = "https://github.com" + a.get('href')
            break
        if pkg_resources.parse_version(rData['version']) > pkg_resources.parse_version(__version__):
          releaseData.append(rData)
      return releaseData
    except Exception as e:
      self.console.print("Failed to parse GitHub release page for upgrade information.", style="err")
      return None

  def _download_upgrade_progress(self, exeURL, version, writePath):
    import requests
    downloadProgress = Progress(TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
                                BarColumn(bar_width=None),"[progress.percentage]{task.percentage:>3.1f}%",
                                "•",DownloadColumn(), "•", TransferSpeedColumn(), "•",TimeRemainingColumn(),
                                console=self.console)
    dlTask = downloadProgress.add_task("download", filename="DCSLM.exe v" + version, start=False)
    dlSize = Utilities.request_file_size(exeURL)
    downloadProgress.update(dlTask, total=dlSize)
    callbackData = { 'exec': self._download_archive_rich_callback, 'progress': downloadProgress, 'task': dlTask }
    with downloadProgress:
      try:
        with requests.get(exeURL, stream=True) as req:
          req.raise_for_status()
          with open(writePath, 'wb') as f:
            if callbackData:
              callbackData['progress'].start_task(callbackData['task'])
            for chunk in req.iter_content(chunk_size=8192):
              f.write(chunk)
              if callbackData:
                callbackData['exec'](callbackData, len(chunk))
        return writePath
      except (KeyboardInterrupt, IOError, ConnectionError, FileNotFoundError) as e:
        if os.path.isfile(writePath):
          Utilities.remove_file(writePath)
        raise RuntimeError("Failed to download \'DCSLM.exe\': " + str(e))
    return None

  def upgrade_dcslm(self):
    import shutil
    import time
    import subprocess
    try:
      releaseData = self.request_upgrade_information()
      if not len(releaseData):
        self.console.print("Current [exe]DCSLM[/exe] version " + __version__ + " is the latest available version.")
      else:
        for rd in releaseData:
          self.console.print(rd['name'] + " (" + rd['version'] + ") " + rd['date'] + ":")
          splitDesc = str.split(rd['desc'], '\n')
          for descLine in splitDesc:
            if len(descLine):
              self.console.print(" - " + descLine)
        self.console.print("")
        upgradeConf = Confirm.ask("Do you want to download and upgrade to the latest version of [exe]DCSLM[/exe]?")
        self.console.print("")
        if upgradeConf:
          oldExec = sys.executable + '.old'
          if os.path.isfile(oldExec):
            try:
              Utilities.remove_file(oldExec)
            except Exception as e:
              self.console.print("[err]Failed to remove old executable:[/err] [red]" + str(e))
          shutil.move(sys.executable, oldExec)
          dlFilename = "DCSLM.exe"
          dlPath = os.path.join(os.getcwd(), dlFilename)
          latestExe = self._download_upgrade_progress(releaseData[0]['download'], releaseData[0]['version'], dlPath)
          if not latestExe:
            shutil.move(oldExec, sys.executable)
            return
          os.chmod(dlFilename, 0o775)
          self.console.print("[bold green][exe]DCSLM[/exe] Upgrade complete to version " + releaseData[0]['version'])
          self.console.print("[exe]DCSLM[/exe] [err]will be restarted in a few moments...")
          time.sleep(2.5)
          subprocess.call(dlFilename)
          sys.exit(0)
    except Exception as e:
      self.console.print("[err][exe]DCSLM[/exe] upgrade failed:[/err] [red]" + str(e))

  def _print_optimization_report(self, optimizationReport):
    if len(optimizationReport):
      optimizationTable = Table(title="Livery Optimization Report", expand=False, box=box.ROUNDED, caption_justify="center")
      optimizationTable.add_column("ID", justify="center", no_wrap=True, style="sky_blue1", width=9)
      optimizationTable.add_column("Livery Title", justify="center", style="")
      optimizationTable.add_column("# Liveries", justify="center", style="magenta")
      optimizationTable.add_column("Hash Matches", justify="center", no_wrap=False, style="green")
      optimizationTable.add_column("Size Before (MB)", justify="right", no_wrap=False, style="bold gold1")
      optimizationTable.add_column("Size After (MB)", justify="right", no_wrap=False, style="bold green")
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
      optimizationTable.caption_justify = "center"
      optimizationTable.caption = "Total Size Before: [bold gold1]" + Utilities.mb_to_mb_string(totalSizeBefore) + \
                                  "[/bold gold1] Mb\tTotal Size After: [bold green]" + Utilities.mb_to_mb_string(totalSizeAfter) + \
                                  " [/bold green]Mb\tTotal Size Delta: [bright_cyan]" + Utilities.mb_to_mb_string(totalSizeDelta) + \
                                  " [/bright_cyan]Mb"

      self.console.print(optimizationTable)

  def optimize_livery(self, sArgs):
    if not len(sArgs):
      raise RuntimeWarning("No liveries provided for \'optimize\' command.")
    sArgs = self._remove_brackets_sArgs(sArgs)
    optimizeArgs = self._parse_command_args("optimize", sArgs)
    removeFiles = not optimizeArgs.keepunused
    optimizationReports = []
    liveryIDs = []
    if len(optimizeArgs.livery) and str.lower(optimizeArgs.livery[0]) == "all":
      confirmAll = Confirm.ask(
        "Do you want to optimize all [bright_cyan]" + str(self.lm.get_num_registered_liveries()) +
        "[/bright_cyan] registered liveries?", console=self.console)
      if confirmAll:
        liveryIDs = list(self.lm.get_registered_livery_ids())
      else:
        return
    else:
      for l in optimizeArgs.livery:
        if l not in liveryIDs:
          liveryIDs.append(l)
    if not len(liveryIDs):
      self.console.print("No liveries given to \'optimize\' command.")
      return
    liveryIndex = 0
    for l in liveryIDs:
      livery = self.lm.get_registered_livery(id=l)
      liveryIndex += 1
      progressStr = "[" + str(liveryIndex) + "/" + str(len(liveryIDs)) + "] "
      if livery:
        if not 'optimized' in livery.installs.keys() or not livery.installs['optimized'] or optimizeArgs.reoptimize:
          if not optimizeArgs.check:
            self.console.print(progressStr + "Optimizing livery \'" + livery.dcsuf.title + "\'")
          else:
            self.console.print(progressStr + "Checking livery optimization (--check) \'" + livery.dcsuf.title + "\'")
          filesData = self.lm.optimize_livery(livery, copyDesc=optimizeArgs.keepdesc, removeUnused=removeFiles,
                                              checkOnly=optimizeArgs.check)
          if filesData:
            if not optimizeArgs.check:
              livery.installs['optimized'] = True
            optimizationData = {'matches': len(filesData['same_hash']),
                                'size_before': filesData['size']['before'],
                                'size_after': filesData['size']['after'],
                                'livery': livery}
            optimizationReports.append(optimizationData)
            if len(filesData['missing']):
              for t in filesData['missing'].keys():
                missingFilesStr = ', '.join(filesData['missing'][t])
                self.console.print(progressStr + "[red]Missing files referenced in description.lua for " + t + ": "
                                   + missingFilesStr)
            liveryReportStr = "Matched " + str(len(filesData['same_hash'])) + " image files with the same content."
            if removeFiles and not optimizeArgs.check:
              liveryReportStr += " Removed " + str(len(filesData['unused'])) + " unused files.\n"
              if len(filesData['unused']) > 0:
                self.console.print(filesData['unused'])
                liveryReportStr += "Size Before: [bold gold1]" + Utilities.bytes_to_mb_string(filesData['size']['before']) + \
                                   "[/bold gold1] Mb\t"
                liveryReportStr += "Size After: [bold green]" + Utilities.bytes_to_mb_string(filesData['size']['after']) + \
                                   "[/bold green] Mb\t"
                liveryReportStr += "Size Delta: " + Utilities.bytes_to_mb_string(filesData['size']['after'] - filesData['size']['before']) + " Mb\n"
            self.console.print(progressStr + liveryReportStr)
            if optimizeArgs.verbose:
              pprint(filesData)
        else:
          self.console.print(progressStr + "Skipping re-optimizing livery \'" + livery.dcsuf.title + "\'.")
      else:
        self.console.print(progressStr + "[red]No livery found for input \'" + l + "\'.")
    if not optimizeArgs.check:
      with self.console.status("Updating livery .dcslm files..."):
        for op in optimizationReports:
          l = op['livery']
          self.lm.write_livery_registry_files(l)
        self.lm.write_data()
    self._print_optimization_report(optimizationReports)

  def _make_unit_panel(self, unitData):
    unitTable = Table.grid(expand=False, padding=(0, 2, 2, 0))
    unitTable.add_column("Info", justify="right", no_wrap=True, style="sky_blue1")
    unitTable.add_column("Content", justify="left")
    unitTable.add_row("Generic Name", unitData.generic)
    unitTable.add_row("Friendly Name", unitData.friendly)
    if unitData.dcs_files:
      unitTable.add_row("DCS User Files Name", unitData.dcs_files)
    unitTable.add_row("Names/Tags", Text("[" + ', '.join(unitData.names) + "]"))
    unitTable.add_row("Livery Folders", Text("[" + ', '.join(unitData.liveries) + "]"))
    unitAlign = Align(unitTable, align="center")
    unitTitle = unitData.friendly + " Config"
    if unitData.custom:
      unitTitle = "[unit.custom]" + unitTitle # + " (CUSTOM)"
    elif unitData.modified:
      unitTitle = "[unit.modified]" + unitTitle # + " (MODIFIED)"
    else:
      unitTitle = "[green]" + unitTitle
    unitPanel = Panel(unitAlign, title=unitTitle, highlight=True, expand=False)
    return unitPanel

  def dcs_units(self, sArgs):
    if len(sArgs):
      unitsArgs = self._parse_command_args("units", sArgs)
      unitName = ' '.join(unitsArgs.unit)
      unitData = UM.get_unit_from_friendly_name(unitName.lower())
      if unitData:
        if unitsArgs.export:
          if unitData.custom or unitData.modified:
            self.console.print("Unit config for \'" + unitData.friendly + "\' is the same on disk.")
          else:
            self.console.print("Writing out config for \'" + unitData.friendly + "\' to \'[exe]DCSLM[/exe]\\units\\" +
                               unitData.category.lower() + "/" + unitData.generic + ".json\'")
            UM.write_unit_config_file(unitData)
        else:
          unitPanel = self._make_unit_panel(unitData)
          self.console.print(unitPanel)
      else:
        self.console.print("Unable to find matching unit from \'" + unitName + "\'.")
    else:
      for c in UM.Categories:
        if c in UM.Units.keys():
          friendlyUnits = []
          for n,u in UM.Units[c].items():
            friendlyStr = u.friendly
            if u.custom:
              friendlyStr = "[unit.custom]" + friendlyStr + "[/unit.custom]"
            elif u.modified:
              friendlyStr = "[unit.modified]" + friendlyStr + "[/unit.modified]"
            elif u.generic in UnitsOfficial[c]:
              friendlyStr = "[unit.official]" + friendlyStr + "[/unit.official]"
            friendlyUnits.append(friendlyStr)
          unitsStr = ', '.join(friendlyUnits)
          subtitleStr = "Unit ── [unit.official]Official[/unit.official] ── "
          subtitleStr += "[unit.modified]Modified[/unit.modified] ── "
          subtitleStr += "[unit.custom]Custom[/unit.custom]"
          self.console.print(Panel(unitsStr, title="[bold sky_blue1]" + c + " Units", expand=False, highlight=False,
                                   subtitle=subtitleStr, subtitle_align="center"), justify="center")

  def dcslm_config(self, sArgs):
    for i in range(0, len(sArgs)):
      if sArgs[i] in self.commands['config']['subcommands'].keys():
        sArgs[i] = "--" + sArgs[i]
    configArgs = self._parse_command_args("config", sArgs)
    if not len(sArgs) or (not configArgs.lm and not configArgs.dcsuf):
      self.console.print("No arguments provided for \'config\' command.")
    else:
      if configArgs.lm:
        if configArgs.export:
          writeData = self.lm.write_data()
          if writeData:
            self.console.print("Wrote [exe]DCSLM[/exe] configuration to \'[exe]DCSLM[/exe]\\dcslm.json\'")
          else:
            self.console.print("[red]Failed to write [sky_blue1]Livery Manager[/sky_blue1] configuration to " +
                               "\'[exe]DCSLM[/exe]\\dcslm.json\'[/red]")
        elif configArgs.reload:
          lmData = self.lm.load_data()
          if lmData:
            self.lm.LiveryData = lmData
            self.console.print("Loaded [sky_blue1]Livery Manager[/sky_blue1] configuration settings from " +
                               "\'[exe]DCSLM[/exe]\\dcslm.json\'")
          else:
            self.console.print("[red]Failed to read in [sky_blue1]Livery Manager[/sky_blue1] configuration settings " +
                               "from \'[exe]DCSLM[/exe]\\dcslm.json\'[/red]")
        else:
          lmTable = Table(title="[sky_blue1]Livery Manager[/sky_blue1] Configuration", box=box.ROUNDED,
                          show_header=False, min_width=30)
          lmTable.add_column("Variable", justify="right", style="bold gold1")
          lmTable.add_column("Value", justify="left")
          for v,s in self.lm.LiveryData['config'].items():
            lmTable.add_row(v, str(s))
          self.console.print(lmTable)
          self.console.print("")
      elif configArgs.dcsuf:
        if configArgs.export:
          writePath = DCSUFPC.write_config()
          if writePath and os.path.isfile(writePath):
            self.console.print("Wrote out current [sky_blue1]DCS User Files Parsing[/sky_blue1] configuration to " +
                               "\'[exe]DCSLM[/exe]\\dcsuf_parse.json\'")
          else:
            self.console.print("[red]Failed to write [sky_blue1]DCS User Files Parsing[/sky_blue1] configuration to " +
                               "\'[exe]DCSLM[/exe]\\dcsuf_parse.json\'[/red]")
        elif configArgs.reload:
          if DCSUFPC.load_config_file():
            self.console.print("Loaded [sky_blue1]DCS User Files Parsing[/sky_blue1] configuration settings from " +
                               "\'[exe]DCSLM[/exe]\\dcsuf_parse.json\'")
            self.completers['units']['dict'] = self.make_units_completer()
            self._make_nested_completers()
          else:
            self.console.print("[red]Failed to read [sky_blue1]DCS User Files Parsing[/sky_blue1] configuration " +
                               "settings from \'[exe]DCSLM[/exe]\\dcsuf_parse.json\'[/red]")
        else:
          dcsufTable = Table(title="[sky_blue1]DCS User Files Parsing[/sky_blue1] Configuration", box=box.ROUNDED,
                             show_header=False)
          dcsufTable.add_column("Variable", justify="right", style="bold gold1")
          dcsufTable.add_column("Value", justify="left")
          for v,s in DCSUFPC.DCSUFDivConfig.items():
            dcsufTable.add_row(v, str(s))
          self.console.print(dcsufTable)

  def prompt_dcsuf_info(self, titles=None, display=True, livery=None, unit=None):
    from DCSLM.Livery import DCSUserFile
    from DCSLM.Unit import Unit
    dcsuf = None
    usedDCSUF = False
    selectedUnit = None
    panelUnit = "None"
    self.console.print("Prompting user for DCS User Files livery information\n")
    self.console.print("Fill in the information with the \'DCS User Files ID\' or leave the line blank and hit [bold]ENTER[/bold].")
    dcsufID = Prompt.ask("[bold]DCS User Files ID[/bold]", console=self.console)
    if dcsufID and len(dcsufID):
      if dcsufID.isnumeric():
        id = int(dcsufID)
        if id > self.lm.IDLocalMax:
          self.console.print("Getting DCS User Files information from ID " + str(id))
          parsedDCSUF = DCSUFParser().get_dcsuserfile_from_url(dcsufID)
          if parsedDCSUF:
            liveryUnitData = UM.get_unit_from_dcsuf_text(parsedDCSUF.unit)
            if liveryUnitData:
              panelUnit = liveryUnitData.friendly
              parsedDCSUF.unit = liveryUnitData
            self.console.print("Successfully parsed data from DCS User Files (" + str(id) + ").")
            dcsuf = parsedDCSUF
          else:
            self.console.print("Failed to parse data from DCS User Files (" + str(id) + ").")
        else:
          self.console.print(str(id) + " not high enough for a valid DCS User Files ID (>" + str(self.lm.IDLocalMax) + ").")
      else:
        self.console.print("\'" + dcsufID + "\' not a valid number.")
    if dcsuf:
      self.print_dcsuf_panel(dcsuf, panelUnit, True)
      if Confirm.ask("[bold]Confirm DCS User Files Information[/bold]", console=self.console):
        usedDCSUF = True
        return dcsuf, usedDCSUF
      else:
        dcsuf = None
    else:
      confirmData = False
      dcsuf = DCSUserFile()
      self.console.print("\n[bold]Please manually enter livery information. Some fields are optional.")
      promptTitles = []
      choiceStr = "\t[0] Custom Title"
      if titles and len(titles):
        promptTitles = [t for t in titles]
        for i in range(0, len(titles)):
          choiceStr += "\n\t[" + str(i + 1) + "] " + titles[i]
      while not confirmData:
        while not dcsuf.title:
          self.console.print("[bold]\nLivery Title Choices:")
          self.console.print(choiceStr)
          numChoices = [str(i) for i in range(0, len(promptTitles) + 1)]
          tChoice = Prompt.ask("\n[bold]Select Livery Title[/bold]", console=self.console, choices=numChoices)
          if tChoice:
            if tChoice == "0":
              customTitle = Prompt.ask("[bold]Enter custom livery title[/bold]", console=self.console)
              if len(customTitle):
                dcsuf.title = customTitle
              else:
                self.console.print("Invalid custom livery title.")
            else:
              dcsuf.title = promptTitles[int(tChoice) - 1]
          if dcsuf.title:
            self.console.print("Using \'" + dcsuf.title + "\' as livery title.")
        while not dcsuf.unit:
          if unit:
            selectedUnit = unit
            panelUnit = unit.friendly
            dcsuf.unit = unit.generic
            self.console.print("Using \'" + unit.friendly + "\' as livery unit.")
          else:
            unitInput = self._install_prompt_unit_input()
            if unitInput:
              dcsuf.unit = unitInput
            if dcsuf.unit:
              self.console.print("Using \'" + unitInput.friendly + "\' as livery unit.")
              selectedUnit = unitInput
              panelUnit = unitInput.friendly
        while not dcsuf.author:
          authorInput = Prompt.ask("[bold](OPTIONAL) Enter livery author[/bold]", console=self.console)
          if not authorInput or (authorInput and len(authorInput) == 0):
            dcsuf.author = "None"
          else:
            dcsuf.author = authorInput.strip()
          if dcsuf.author:
            self.console.print("Using \'" + dcsuf.author + "\' as livery author.")
        dataCheckChoices = ['c','t','u','a']
        self.console.print("\n\t[[sky_blue1]c[/sky_blue1]]onfirm Data")
        self.console.print("\t[[sky_blue1]t[/sky_blue1]]itle: [green]" + dcsuf.title)
        self.console.print("\t[[sky_blue1]u[/sky_blue1]]nit: [bold magenta]" + dcsuf.unit.friendly)
        self.console.print("\t[[sky_blue1]a[/sky_blue1]]uthor: [bold gold1]" + dcsuf.author)
        checkConfirm = Prompt.ask("\n[bold]Confirm or edit livery information[/bold]", console=self.console, choices=dataCheckChoices)
        if checkConfirm == 't':
          dcsuf.title = None
        elif checkConfirm == 'u':
          dcsuf.unit = None
          unit = None
        elif checkConfirm == 'a':
          dcsuf.author = None
        else:
          confirmData = True
    generatedID = self.lm.get_next_local_livery_id()
    dcsuf.id = generatedID
    self.console.print("Generated Livery ID " + str(generatedID))
    dcsuf.tags = []
    if not livery:
      dcsuf.datetime = datetime.now()
      dcsuf.date = dcsuf.datetime_to_date(dcsuf.datetime)
      dcsuf.size = "0"
      dcsuf.download = ""
    else:
      dcsuf.datetime = livery.dcsuf.datetime
      dcsuf.date = livery.dcsuf.date
      dcsuf.size = livery.dcsuf.size
      dcsuf.download = livery.dcsuf.download
    if display and selectedUnit:
      self.print_dcsuf_panel(dcsuf, unitName=panelUnit)
    return dcsuf, usedDCSUF

  def print_help(self):
    for k, v in self.commands.items():
      self.console.print("[deep_pink2]" + k + "[/deep_pink2] [sky_blue1]" + v['usage'] + "[/sky_blue1]")
      self.console.print("\t" + v['desc'])
      if len(v['args']):
        printedArgHeader = False
        hasOptional = False
        for j, l in v['args'].items():
          if not l['optional']:
            if not printedArgHeader:
              self.console.print("\t[bold]Arguments:[/bold]")
              printedArgHeader = True
            self.console.print("\t\t[bold]" + j + "[/bold] (" + l['type'] + ") - " + l['desc'])
          else:
            hasOptional = True
        if hasOptional:
          self.console.print("\t[bold]Optional Arguments:[/bold]")
          for j, l in v['args'].items():
            if l['optional']:
              self.console.print("\t\t[bold]" + j + "[/bold] (" + l['type'] + ") - " + l['desc'])
      if len(v['subcommands']):
        self.console.print("\t[bold]Subcommands:[/bold]")
        for j, l in v['subcommands'].items():
          self.console.print("\t\t[bold]" + j + "[/bold] - " + l['desc'])
      if len(v['flags']):
        self.console.print("\t[bold]Flags:[/bold]")
        for j, l in v['flags'].items():
          self.console.print("\t\t[bold]" + ', '.join(l['tags']) + "[/bold] - " + l['desc'])

  def _center_justify_lines(self, strList, maxWidth=-1):
    maxLen, maxIndex = 0, -1
    justifiedList = []
    for i in range(0, len(strList)):
      if len(strList[i]) > maxLen:
        maxLen = len(strList[i])
        maxIndex = i
    if maxIndex != -1:
      if maxWidth != -1:
        maxLen = min(maxLen, maxWidth)
      for i in range(0, len(strList)):
        if i == maxIndex:
          justifiedList.append(strList[i])
          continue
        justifiedList.append(strList[i].center(maxLen, ' '))
    else:
      return strList
    return justifiedList

  def _make_dcsuf_panel(self, dcsuf, childPanel=False, unitName="", showTags=False):
    from DCSLM.Livery import DCSUserFile
    dcsufLines = ["ID: " + str(dcsuf.id) + " | Author: " + dcsuf.author + " | Upload Date: " +
                  dcsuf.date + " | Archive Size: " + dcsuf.size,
                  dcsuf.download]
    if showTags:
      dcsufLines.append("Tags: " + ', '.join(dcsuf.tags))
    maxWidth = self.console.width
    if childPanel:
      maxWidth -= 8
    justifiedLines = self._center_justify_lines(dcsufLines, maxWidth)
    authIndex = justifiedLines[0].find("Author: ") + len("Author: ")
    endAuthIndex = justifiedLines[0].find("|", authIndex)
    justifiedLines[0] = justifiedLines[0][:authIndex] + "[bold gold1]" + justifiedLines[0][authIndex:endAuthIndex - 1] \
                        + "[/bold gold1]" + justifiedLines[0][endAuthIndex - 1:]
    if showTags:
      justifiedLines[2] = "[sky_blue1]" + justifiedLines[2][:5] + "[/sky_blue1]" + justifiedLines[2][5:]
    dcsufStr = "\n".join(justifiedLines)

    return Panel(dcsufStr, title="[bold green]" + unitName + "[/bold green] - [sky_blue1]" + dcsuf.title,
                 expand=False, highlight=True)

  def print_dcsuf_panel(self, dcsuf, unitName="", showTags=False):
    if dcsuf:
      self.console.print(self._make_dcsuf_panel(dcsuf, unitName=unitName, showTags=showTags))

  def make_commands_completer(self):
    completerDict = {}
    for k, v in self.commands.items():
      if v['hidden']:
        continue
      completerDict[k] = None
    return completerDict

  def make_units_completer(self):
    completerDict = {}
    for t in UM.Units.keys():
      for u,d in UM.Units[t].items():
        completerDict[d.friendly] = None
    return completerDict

  def make_livery_ids_completer(self):
    completerDict = {}
    for id,l in self.lm.Liveries.items():
      fullID = str(id) + " [" + l.dcsuf.title + "]"
      completerDict[fullID] = None
    return completerDict

  def clear_and_print_header(self):
    from DCSLM.ascii_logos import DCSLM_ASCII
    import datetime
    import random
    currentDT = datetime.datetime.now()
    if currentDT.month == 10 and currentDT.day == 31:
      randLogo = DCSLM_ASCII['spooky']
    else:
      randLogo = random.choice(list(DCSLM_ASCII['random'].values()))
    clear_console()
    for l in randLogo:
      self.console.print(l, style="bold sky_blue1", justify="center", highlight=False)
    self.console.print(f"v{__version__}", style="bold gold1", justify="center", highlight=False)
    self.console.print('')

  def setup_rich_console_theme(self):
    themeConfig = {
      'path': "bold green",
      'title': "magenta",
      'size': "bold gold1",
      'size.opt': "green",
      'unit': "green",
      'unit.official': "green",
      'unit.modified': "bold gold1",
      'unit.custom': "magenta",
      'warn': "bold gold1",
      'err': "bold red",
      'exe': "sky_blue1",
      'num': "bright_cyan"
    }
    dcslmTheme = Theme(themeConfig)
    self.theme = dcslmTheme

  def setup_console_window(self):
    self.console = Console(tab_size=4, theme=self.theme)

  def setup_livery_manager(self):
    self.console.print("DCSLM.exe Directory: \'" + os.getcwd() + "\'")
    self.lm = LiveryManager()
    self.lm.console = self.console
    lmData = self.lm.load_data()
    if not lmData:
      self.console.print("No existing \'[exe]DCSLM[/exe]\\dcslm.json\' file found with config and livery data. Loading defaults.")
      if not "Saved Games" in os.getcwd() and not "DCS" in os.getcwd().split("\\")[-1]:
        self.console.print("[red][exe]DCSLM[/exe] has detected it's not within a[/red] [bold gold1]DCS Saved Games[/bold gold1] " +
                           "[red]directory.")
        self.prompt_livery_manager_defaults()
      self.lm.make_dcslm_dirs()
      self.lm.write_data()
    else:
      self.console.print("Loaded Livery Manager config and data from \'[exe]DCSLM[/exe]\\dcslm.json\'")
      self.lm.LiveryData = lmData

  def setup_unit_manager(self):
    UM.setup_unitmanager()

  def prompt_livery_manager_defaults(self):
    if self.lm:
      self.console.print("\n\n[bold green underline]Mod Manager Mode:")
      self.console.print("If you use a mod manager, like \'OVGME\' or \'JSGME\', to manage your DCS mod installs, " +
                         "you can enable \'Mod Manager Mode\' to have it create a root directory named with the " +
                         "livery title when installing a livery.")
      self.console.print("\n[bold gold1]For \'Mod Manager Mode\' make sure you've placed \'[exe]DCSLM[/exe].exe\' inside your " +
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

  def prompt_aircraft_livery_choice(self, livery, unitChoices):
    liveryChoices = ["[white]None[/white]"]
    liveryUnitData = livery.dcsuf.unit
    for u in unitChoices:
      unitData = UM.get_unit_from_generic_name(u)
      if unitData:
        liveryChoices.append("[white]" +  unitData.friendly + "[/white]")
      else:
        liveryChoices.append(u)
    liveryChoices.append("[bold white]All[/bold white]")
    if len(liveryChoices) > 3:
      choiceText = ""
      for i in range(0, len(liveryChoices)):
        choiceText += "[[sky_blue1]" + str(i) + "[/sky_blue1]]" + liveryChoices[i] + " "
      self.console.print("\nThere are multiple livery install locations for the [bold magenta]" +
                         liveryUnitData.friendly + "[/bold magenta]. " +
                         "Please choose from the following choices by inputting the corresponding index number(s):")
      self.console.print("\n\t" + choiceText)
      try:
        promptStr = "\n[bold]Which units do you want the livery to be installed to?[/bold]"
        optionsStr = '/'.join([str(i) for i in range(0,len(liveryChoices))])
        validChoice = False
        while not validChoice:
          choices = self.console.input(promptStr + " [magenta][" + optionsStr + "]: ")
          choices = choices.split(' ')
          chosenUnits = []
          if "0" in choices:
            return chosenUnits
          elif str(len(liveryChoices) - 1) in choices:
            chosenUnits = unitChoices
          else:
            for c in choices:
              if int(c) <= len(unitChoices) and int(c) >= 1:
                chosenUnits.append(unitChoices[int(c) - 1])
            if len(chosenUnits) == 0:
              self.console.print("[red]Invalid unit selection.")
              continue
          self.console.print("Installing to units [sky_blue1]" + '[white],[/white] '.join(chosenUnits) + "[/sky_blue1]")
          return chosenUnits
      except KeyboardInterrupt:
        return []

  def check_7z_installed(self):
    if not get_nt_7z_dir():
      self.console.print("")
      self.console.print("[red]7-Zip was not found in the environment PATH. Make sure you have 7-Zip installed or " +
                         "this program will not work correctly!")
      self.console.print("[red]7-Zip is a free program available at[/red] https://www.7-zip.org/download.html")

  def check_last_update(self):
    currentTime = datetime.now()
    if not "last_update" in self.lm.LiveryData.keys():
      self.lm.LiveryData['last_update'] = 0
    numLiveries = self.lm.get_num_registered_liveries()
    if numLiveries > 0:
      if self.lm.LiveryData['last_update'] == 0:
        self.console.print("Use the [deep_pink2]update[/deep_pink2] command to see if there are updates available for " +
                           str(numLiveries) + " registered liveries.", style="gold1")
      else:
        lastUpdateTime = datetime.fromtimestamp(self.lm.LiveryData['last_update'])
        timeSinceUpdate = currentTime - lastUpdateTime
        if timeSinceUpdate.days > 0:
          self.console.print("[bold]" + str(timeSinceUpdate.days) + " days[/bold] since last check of updates for " +
            str(numLiveries) + " registered liveries.")

  def set_last_update(self):
    self.lm.LiveryData['last_update'] = datetime.timestamp(datetime.now())

  def print_motd(self):
    if self.lm.get_num_registered_liveries() > 0:
      liveryMB = self.lm.get_size_registered_liveries()
      if liveryMB > 10000.0:
        sizeStr = Utilities.mb_to_gb_string(liveryMB) + " [bold gold1]GB[/bold gold1]"
      else:
        sizeStr = Utilities.mb_to_mb_string(liveryMB) + " [bold gold1]MB[/bold gold1]"
      self.console.print(str(self.lm.get_num_registered_liveries()) + " registered liveries (" + sizeStr +")")

  def _download_archive_rich_callback(self, dlCallback, downloadedBytes):
    dlCallback['progress'].update(dlCallback['task'], advance=downloadedBytes)

  def _download_archive_progress(self, livery, session=None):
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
      archivePath =  self.lm.download_livery_archive(livery, dlCallback=callbackData, session=session)
    return archivePath

  def reload_dcslm_config(self):
    if self.lm:
      self.lm.clear_data()
      self.lm.LiveryData = self.lm.load_data()

  def _executable_parse_list_command(self, command, varData):
    parsedCommands = []
    for s in varData:
      splitS = str.split(s, " ")
      for x in range(0, len(splitS)):
        spS = splitS[x]
        if len(spS) == 0 or spS == command:
          continue
        parsedCommands.append(spS)
    return parsedCommands

  def parse_exe_args(self):
    self.parsedArgs = self._parse_command_args("executable", sys.argv[1:])

  def run_exe_args(self):
    if len(sys.argv) == 1:
      return False
    exeArgsStr = "\t[sky_blue1]DCSLM.exe[/sky_blue1] "
    runnableCommand = False
    for a in sys.argv[1:]:
      if len(a):
        if a[0] == "-":
          exeArgsStr += a + " "
          if a != "-w" and a != "--workingdirectory":
            runnableCommand = True
        else:
          exeArgsStr += "[italic]" + a + "[/italic] "
    if runnableCommand:
      self.console.print("")
      self.console.print("Running [exe]DCSLM[/exe] executable arguments:", style="bold gold1")
      self.console.print(exeArgsStr)
      if self.parsedArgs.persist:
        self.console.print("[exe]DCSLM[/exe] will remain [green italic]open[/green italic] after completion (-p, --persist)", style="blue")
      else:
        self.console.print("[exe]DCSLM[/exe] will [red italic]close[/red italic] after completion", style="blue")
    parseConfig = {
      'uninstall': {'parsedArgs': self.parsedArgs.uninstall, 'exec': self.uninstall_liveries},
      'install': {'parsedArgs': self.parsedArgs.install, 'exec': self.install_liveries},
      'update': {'parsedArgs': self.parsedArgs.update, 'exec': self.update_liveries},
      'upgrade': {'parsedArgs': self.parsedArgs.upgrade, 'exec': self.upgrade_dcslm}
    }
    ranExeArg = False
    for f,c in parseConfig.items():
      try:
        if c['parsedArgs']:
          self.console.print("")
          if isinstance(c['parsedArgs'], list):
            parsedCommandArgs = self._executable_parse_list_command(f, c['parsedArgs'])
            if len(parsedCommandArgs):
              c['exec'](parsedCommandArgs)
          else:
            c['exec']()
          ranExeArg = True
      except Exception as e:
        self.console.print(e, style="err")
    return ranExeArg

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
                self.console.print(e, style="err")
            self.console.print("")
            if splitCommand[0] == "exit":
              runCommands = False
          else:
            self.console.print("Command \'" + splitCommand[0] + "\' not found.")

  def dcslm_exit(self, prompt=False):
    if prompt:
      self.console.print("\n[exe]DCSLM[/exe] will now close...")
      os.system("pause")
    self.console.print("Writing out current config and livery data to \'[exe]DCSLM[/exe]/dcslm.json\'")
    self.lm.write_data()
    self.console.print("Exiting DCS Livery Manager.")

if __name__ == '__main__':
  set_console_title(f'DCS Livery Manager v{__version__}')
  dcslmapp = DCSLMApp()
  dcslmapp.start()

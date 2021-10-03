# DCSLiveryManager
TUI tool to download, install, and update your DCS liveries from DCS User Files.

# About
Installing liveries for DCS isn't the most streamlined experience as the livery files can come in various forms of archive file types, may have some form of folder hierarchy or none at all, and can contain multiple liveries! The DCS Liveries Manager (DCSLM) aims to make that same experience as simple as possible. 

DCSLM is setup to handle multiple archive types (see pre-requisites) and any sort of folder hierachy contained within all from the URL or DCS User Files ID! DCSLM will register the livery and allows you to check for updated versions of the same livery uploaded to DCS User Files.

# Pre-Requisites
DCSLM relies on the [patool](https://pypi.org/project/patool/), which in turn relies on the installed archive programs you have on your computer. It's **highly** recommended you install [7-Zip](https://www.7-zip.org/download.html) as it's a free, open-source program that can handle any archive you will encounter on DCS User Files. You must make sure the 7z install directory is on your path for it to work correctly.

Your anti-virus software may flag *DCSLM.exe* and attempt to remove it due to it being a unsigned and untrusted executable. Very understandable! You may need to add an exception to stop that from happening. I promise nothing funky is going on in this program, check the source code!

# Installation
DCSLM is packaged as a single Windows EXE that needs to be placed in the proper directory depending on your setup:
* Place *DCSLM.exe* in your DCS Saved Games directory (i.e. C:\Users\sneep\Saved Games\DCS)
* For use with a mod manager, like OVGME or JSGME, you should place *DCSLM.exe* in the folder that is configured to be installed to your DCS Saved Games directory. You must make sure to enable ***Mod Manager Mode*** when you first run DCSLM.
* **Do NOT place it in your core DCS install directory**.

# Quick Usage
Installing liveries is as simple as running the `install` command with any number of DCS User Files URLs or IDs:

`install https://www.digitalcombatsimulator.com/en/files/3312290/ 3313120 3313121 digitalcombatsimulator.com/en/files/3313122/`

https://user-images.githubusercontent.com/37012295/116582045-cca21800-a8c9-11eb-83d0-62cc36679c68.mp4

# Commands
There are many commands available in DCSLM. Here are quick explanations of each command and how they are used. For more complete instructions, argument explanations, and usage you can use the `help` command within DCSLM.

## install
The `install` command takes any number of DCS User Files URLs or IDs (taken from the last part of the URL) and attempts to install those liveries. You will be prompted to select which units to install to when there are multiple choices available (i.e. A-10, F-14). When installing a livery in the *Other* category, DCSLM will attempt to use the tags to attempt to match a unit, and if it can't you will be prompted to choose one. These tags are defined in the *unit files* (see `units` command below).

## uninstall
The `uninstall` command takes any number of installed livery IDs and will remove the files and directories from disk.

## info
The `info` command displays information about the given livery, such as its DCS User Files info, the unit it's installed to, the names of the liveries installed, and the file paths of the directories created.
![info](https://user-images.githubusercontent.com/37012295/135744046-83dae84e-7f21-4ab1-8438-cc158d21b2d2.jpg)

## list
The `list` command displays all installed liveries, what units they're installed to, and their size on disk (including if they've been optimized).
![list](https://user-images.githubusercontent.com/37012295/135744065-5afd5d8b-5d22-4288-b9f0-3388e25b445f.jpg)

## check
The `check` command will go through every installed livery and see if there is a new version uploaded to DCS User Files. The status of each livery will be displayed in a table at the end of the check process.

## update
`update` is like `check` but will download the liveries that have an update available. This is done by re-installing the livery, so you will be given any applicable choice prompts again and if you optimized the livery previously you will need to run the `optimize` command on them again.

## optimize
The `optimize` command is useful when installing a livery with multiple liveries contained within. It will attempt to find shared files and will edit the *description.lua* to correct the filepaths for the different parts. This can be useful for reducing the amount of disk space used when you have many liveries installed. 
![optimize](https://user-images.githubusercontent.com/37012295/135744294-9417d31d-94f4-4913-82a8-c03628741e94.jpg)

## scan
The `scan` command can be used to search your Liveries folder for existing *.dcslm* files to detect installed liveries that are missing from your installed list. This can be useful if your *dcslm.json* saved settings file gets removed or corrupted.

## units
The `units` command displays all the recognized units by DCSLM, and when given a specific unit displays their configuration. By default, these are all the aircraft units selectable on the DCS User Files website. You can use the `units` command to export those default units to modify their settings. DCSLM is setup to import any units defined by .json files in the */DCSLM/units/* directories.
![units_re](https://user-images.githubusercontent.com/37012295/135765565-89bc82ef-73f2-42eb-b04f-35ea0e69c2f6.jpg) ![units_custom_re](https://user-images.githubusercontent.com/37012295/135765532-ea2ae9e1-a0b4-4db0-95f3-d9ea5f3eb670.jpg)

## config
The `config` command can display, reload, or export, the settings for configurable DCSLM systems, such as the DCS User Files Parser. This allows the user to make various changes to some of the DCSLM settings.

## upgrade
The `upgrade` command will download and replace the current *DCSLM.exe* program if there is a newer version available on github.com.

## help
The `help` command displays more information for every command available in DCSLM, such as their arguments, flags, usage, as well as descriptions for those.

## exit
`exit` cleanly exits the DCSLM program. 

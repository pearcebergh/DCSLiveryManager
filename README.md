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
* For user with a mod manager, like OVGME or JSGME, you should place *DCSLM.exe* in the folder that is configured to be installed to your DCS Saved Games directory. You must make sure to enable ***Mod Manager Mode*** when you first run DCSLM.
* **Do NOT place it in your core DCS install directory**.

# Usage
Installing liveries is as simple as running the `install` command with any number of DCS User Files URLs or IDs:

`install https://www.digitalcombatsimulator.com/en/files/3312290/ 3313120 3313121 digitalcombatsimulator.com/en/files/3313122/`

You can get a list of all available commands with descriptions using the `help` command.

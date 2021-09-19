from .Unit import Unit
from .UnitDefaults import UnitDefaults
import os
import json

class UnitManager:
  def __init__(self):
    self.Units = {}
    self.Categories = ["Air", "Ground", "Sea"]
    self.setup_unitmanager()

  def setup_unitmanager(self):
    self.load_defaults()
    self.create_unit_directories()
    self.load_custom()

  def load_defaults(self):
    for unitType in UnitDefaults.keys():
      if not unitType in self.Units:
        self.Units[unitType] = {}
      for unitName, unitData in UnitDefaults[unitType].items():
        defaultUnit = Unit().from_JSON(unitName, unitData)
        self.Units[unitType][unitName] = defaultUnit

  def load_custom(self):
    import glob
    for unitType in self.Categories:
      unitRoot = os.path.join("DCSLM", "units", unitType)
      unitFiles = glob.glob(os.path.join(os.getcwd(), unitRoot, "*.json"))
      for uF in unitFiles:
        unitFilename = os.path.split(uF)[-1]
        unitName = os.path.splitext(unitFilename)[0]
        with open(uF, "r") as unitFile:
          unitData = json.load(unitFile)
          customUnit = Unit().from_JSON(unitName, unitData)
          if customUnit.validate_unit():
            if unitName in self.Units.keys():
              print("Replacing " + unitName + " with data from " + os.path.join(unitRoot, unitFilename))
            else:
              print("Loading custom unit " + unitName)
            self.Units[unitType][unitName] = customUnit

  def create_unit_directories(self):
    unitsRoot = os.path.join(os.getcwd(), "DCSLM", "units")
    if not os.path.exists(unitsRoot):
      os.mkdir(unitsRoot)
    for c in self.Categories:
      categoryPath = os.path.join(unitsRoot, str.lower(c))
      if not os.path.exists(categoryPath):
        os.mkdir(categoryPath)

  def write_unit_default_files(self):
    for unitType in UnitDefaults.keys():
      unitRoot = os.path.join(os.getcwd(), "DCSLM", "units", unitType)
      if not os.path.exists(unitRoot):
        print("No unit directory exists at " + unitRoot + ".")
        continue
      for unitName, unitData in UnitDefaults[unitType].items():
        unitPath = os.path.join(unitRoot, unitName + ".json")
        with open(unitPath, 'w') as unitFile:
          json.dump(unitData, unitFile, indent=4, )
        print("Wrote " + unitPath)

  def get_unit_from_liveries_dir(self, liveryDir):
    for unitType in UnitDefaults.keys():
      for u in self.Units[unitType].values():
        if liveryDir in u.liveries:
          return u
    return None

UM = UnitManager()

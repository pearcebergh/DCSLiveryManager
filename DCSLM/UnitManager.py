from .Unit import Unit
from .UnitDefaults import UnitDefaults
import os
import json

class UnitManager:
  def __init__(self):
    self.Units = {}
    self.Categories = ["Air", "Ground", "Sea"]
    self.UnitNames = {}

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
        defaultUnit.category = unitType
        self.Units[unitType][unitName] = defaultUnit
        self.UnitNames[unitName] = unitType

  def load_custom(self):
    import glob
    for unitType in self.Categories:
      unitRoot = os.path.join("DCSLM", "units", unitType)
      unitFiles = glob.glob(os.path.join(os.getcwd(), unitRoot, "*.json"))
      for uF in unitFiles:
        unitFilename = os.path.split(uF)[-1]
        unitName = os.path.splitext(unitFilename)[0]
        try:
          with open(uF, "r") as unitFile:
            unitData = json.load(unitFile)
            customUnit = Unit().from_JSON(unitName, unitData)
            customUnit.category = unitType
            if customUnit.validate_unit():
              if unitName in self.UnitNames.keys():
                customUnit.modified = True
              else:
                customUnit.custom = True
              self.UnitNames[unitName] = unitType
              self.Units[unitType][unitName] = customUnit
        except Exception as e:
          print("Failed to load unit config \'" + uF + "\'.")

  def create_unit_directories(self):
    dcslmRoot = os.path.join(os.getcwd(), "DCSLM")
    unitsRoot = os.path.join(dcslmRoot, "units")
    if not os.path.exists(dcslmRoot):
      os.mkdir(dcslmRoot)
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
        try:
          with open(unitPath, 'w') as unitFile:
            json.dump(unitData, unitFile, indent=4)
        except Exception as e:
          raise RuntimeError("Failed to write config file to \'" + unitPath + "\'.")
        print("Wrote " + unitPath)

  def write_unit_config_file(self, unitData):
    unitPath = os.path.join(os.getcwd(), "DCSLM", "units", unitData.category.lower())
    unitFilepath = os.path.join(unitPath, unitData.generic + ".json")
    try:
      with open(unitFilepath, 'w') as unitFile:
        json.dump(unitData.to_JSON(), unitFile, indent=4)
    except Exception as e:
      raise RuntimeError("Failed to write config file to \'" + unitFilepath + "\'.")
    return False

  def get_unit_from_liveries_dir(self, liveryDir):
    for unitType in UnitDefaults.keys():
      for u in self.Units[unitType].values():
        if liveryDir in u.liveries:
          return u
    return None

  def get_unit_from_generic_name(self, genericName):
    for c in self.Categories:
      if c in self.Units.keys():
        for u,d in self.Units[c].items():
          if genericName == d.generic:
            return d
    return None

  def get_unit_from_friendly_name(self, friendlyName):
    for c in self.Categories:
      if c in self.Units.keys():
        for u,d in self.Units[c].items():
          if friendlyName.lower() == d.friendly.lower():
            return d
    return None

  def get_unit_from_dcsuf_text(self, dscufText):
    for c in self.Categories:
      if c in self.Units.keys():
        for u,d in self.Units[c].items():
          if dscufText == d.dcs_files:
            return d
    return None

  def get_units_from_tags(self, tagsList):
    matchedUnits = []
    for c in self.Categories:
      if c in self.Units.keys():
        for u,d in self.Units[c].items():
          for t in tagsList:
            if t.lower() in d.names:
              matchedUnits.append(d)
              break
    return matchedUnits

UM = UnitManager()

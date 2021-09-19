import json

class Unit:
  def __init__(self):
    self.generic = "none"
    self.friendly = "None"
    self.names = []
    self.liveries = []
    self.dcs_files = None
    self.category = None
    self.modified = False
    self.custom = False

  def to_JSON(self):
    classVars = vars(Unit())
    selfVars = vars(self)
    jsonUnit = {}
    for var in classVars.keys():
      if "modified" in var or "custom" in var or "category" in var or "generic" in var:
        continue
      jsonUnit[var] = selfVars[var]
    return jsonUnit

  def from_JSON(self, unitName, jsonData):
    if jsonData:
      classVars = vars(Unit())
      for var, data in classVars.items():
        if var in jsonData.keys():
          setattr(self, var, jsonData[var])
      self.generic = str.lower(unitName)
    return self

  def from_JSON_String(self, unitName, jsonStr):
    jsonData = json.loads(jsonStr)
    return self.from_JSON(unitName, jsonData)

  def validate_unit(self):
    errors = []
    if not self.generic or self.generic is "none":
      errors.append("missing generic name")
    if not self.friendly or self.friendly is "None":
      errors.append("missing friendly name")
    if not self.names or len(self.names) == 0:
      errors.append("missing name(s)")
    if not self.liveries or len(self.liveries) == 0:
      errors.append("missing liveries folder name(s)")
    if len(errors):
      errorString = "Unit data validation failed: "
      for e in errors:
        errorString = errorString + e + ", "
      errorString = errorString[:-2]
      print(errorString)
      return False
    return True

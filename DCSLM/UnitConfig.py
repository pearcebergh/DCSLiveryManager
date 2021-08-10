
# TODO: create Unit class
class UnitConfig:
  def __init__(self):
    self.Units = None
    self.setup_config()

  def get_unit_from_text(self, unitText):
    return self.Units['aircraft'][unitText]

  def get_unit_from_liveries_dir(self, liveryDir):
    for u in self.Units['aircraft'].values():
      if liveryDir in u['liveries']:
        return u
    return None

  def setup_config(self):
    self.Units = {
      "aircraft": {
        "a-10a": {
          "names": ["a-10a"],
          "friendly": "A-10A",
          "dcs_files": "A-10A",
          "liveries": ["A-10A", "A-10C", "A-10CII"],
          "core": "CoreMods/aircraft/A-10"
        },
        "a-10c": {
          "names": ["a-10c"],
          "friendly": "A-10C",
          "dcs_files": "A-10C Warthog",
          "liveries": ["A-10A", "A-10C", "A-10CII"],
          "core": "CoreMods/aircraft/A-10"
        },
        "a-10cii": {
          "names": ["a-10cii", "a-10c2"],
          "friendly": "A-10C II",
          "dcs_files": "A-10C II Tank Killer",
          "liveries": ["A-10A", "A-10C", "A-10CII"],
          "core": "CoreMods/aircraft/A-10"
        },
        "ajs-37": {
          "names": ["ajs-37", "viggen"],
          "friendly": "AJS-37",
          "dcs_files": "AJS-37 Viggen",
          "liveries": ["AJS37"],
          "core": "CoreMods/aircraft/AJS37"
        },
        "av-8b": {
          "names": ["av-8b", "harrier"],
          "friendly": "AV-8B",
          "dcs_files": "AV-8B Night Attack V/STOL",
          "liveries": ["AV8BNA"],
          "core": "CoreMods/aircraft/AV8BNA"
        },
        "bf-109k-4": {
          "names": ["bf-109k-4", "bf-109k"],
          "friendly": "Bf 109 K-4",
          "dcs_files": "Bf 109 K-4 Kurfurst",
          "liveries": ["bf-109k-4"],
          "core": "Bazar/Liveries/Bf-109K-4"
        },
        "c-101": {
          "names": ["c-101"],
          "friendly": "C-101",
          "dcs_files": "C-101 Aviojet",
          "liveries": ["C-101CC", "C-101EB"],
          "core": "CoreMods/aircraft/C-101"
        },
        "Christen Eagle II": {
          "names": ["Christen Eagle II"],
          "friendly": "Christen Eagle II",
          "dcs_files": "Christen Eagle II",
          "liveries": ["Christen Eagle II"],
          "core": "CoreMods/aircraft/Christen Eagle II"
        },
        "f-14": {
          "names": ["f-14"],
          "friendly": "F-14",
          "dcs_files": "F-14 Tomcat",
          "liveries": ["f-14b", "f-14a-135-gr"],
          "core": "CoreMods/aircraft/F14"
        },
        "f-15c": {
          "names": ["f-15c", "f-15"],
          "friendly": "F-15C",
          "dcs_files": "F-15C",
          "liveries": ["F-15C"],
          "core": "Bazar"
        },
        "f-16c": {
          "names": ["f-16c","f-16c_50", "f-16"],
          "friendly": "F-16C",
          "dcs_files": "F-16C Viper",
          "liveries": ["F-16C_50"],
          "core": "CoreMods/aircraft/F-16C"
        },
        "f-5e": {
          "names": ["f-5e", "f-5", "f-5e-3"],
          "friendly": "F-5E",
          "dcs_files": "F-5E Tiger",
          "liveries": ["F-5E-3"],
          "core": "CoreMods/aircraft/F-5E"
        },
        "f-86f": {
          "names": ["f-86f", "f-86f sabre"],
          "friendly": "F-86F",
          "dcs_files": "F-86F Sabre",
          "liveries": ["f-86f sabre"],
          "core": "CoreMods/aircraft/F-86"
        },
        "fa-18c": {
          "names": ["fa-18", "fa-18c", "fa-18c_hornet"],
          "friendly": "FA-18C",
          "dcs_files": "F/A-18C Hornet",
          "liveries": ["FA-18C_hornet"],
          "core": "CoreMods/aircraft/FA-18C"
        },
        "fw-190-a-8": {
          "names": ["fw 190 a8", "fw-190-a8", "fw-190-a-8", "fw 190 a-8", "fw190 a8"],
          "friendly": "Fw 190 A-8",
          "dcs_files": "Fw 190 A-8 Anton",
          "liveries": ["fw-109a-8"],
          "core": "CoreMods/WWII Units/FW-190A-8"
        },
        "fw-190-d-9": {
          "names": ["fw 190 d9", "fw-190-d9", "fw-190-d-9", "fw 190 d-9", "fw190 d9"],
          "friendly": "Fw 190 D-9",
          "dcs_files": "Fw 190 D-9 Dora",
          "liveries": ["FW-109D-9"],
          "core": "CoreMods/WWII Units/FW-190D-9"
        },
        "hawk": {
          "names": ["hawk", "hawk t.1a"],
          "friendly": "Hawk",
          "dcs_files": "Hawk T.1A",
          "liveries": ["Hawk"],
          "core": "CoreMods/aircraft/Hawk"
        },
        "i-16": {
          "names": ["i-16"],
          "friendly": "I-16",
          "dcs_files": "I-16",
          "liveries": ["I-16"],
          "core": "CoreMods/aircraft/I-16"
        },
        "j-11a": {
          "names": ["j-11a"],
          "friendly": "J-11A",
          "dcs_files": "J-11A",
          "liveries": ["J-11A"],
          "core": "CoreMods/aircraft/ChinaAssetPack"
        },
        "jf-17": {
          "names": ["jf-17"],
          "friendly": "JF-17",
          "dcs_files": "JF-17 Thunder",
          "liveries": ["JF-17"],
          "core": "CoreMods/aircraft/ChinaAssetPack"
        },
        "ka-50": {
          "names": ["ka-50"],
          "friendly": "Ka-50",
          "dcs_files": "Ka-50",
          "liveries": ["ka-50"],
          "core": "Bazar"
        },
        "l-39": {
          "names": ["l-39"],
          "friendly": "L-39",
          "dcs_files": "L-39 Albatros",
          "liveries": ["L-39C", "L-39ZA"],
          "core": "CoreMods/aircraft/L-39"
        },
        "m-2000c": {
          "names": ["mirage", "m-2000c"],
          "friendly": "M-2000C",
          "dcs_files": "M-2000C",
          "liveries": ["M-2000C"],
          "core": "CoreMods/aircraft/M-2000C"
        },
        "mi-8mtv2": {
          "names": ["mi-8", "mi-8mtv2"],
          "friendly": "Mi-8MTV2",
          "dcs_files": "Mi-8MTV2",
          "liveries": ["mi-8mt"],
          "core": "Bazar"
        },
        "mig-15bis": {
          "names": ["mig-15", "mig-15bis"],
          "friendly": "MiG-15bis",
          "dcs_files": "MiG-15bis",
          "liveries": ["MiG-15bis"],
          "core": "CoreMods/aircraft/MiG-15bis"
        },
        "mig-19p": {
          "names": ["mig-19p"],
          "friendly": "MiG-19P",
          "dcs_files": "MiG-19P Farmer",
          "liveries": ["MiG-19P"],
          "core": "CoreMods/aircraft/MiG-19P"
        },
        "mig-21bis": {
          "names": ["mig-21bis", "mig-21"],
          "friendly": "MiG-21bis",
          "dcs_files": "MiG-21bis",
          "liveries": ["MiG-21Bis"],
          "core": "CoreMods/aircraft/MiG-21Bis"
        },
        "mig-29a": {
          "names": ["mig-29a"],
          "friendly": "MiG-29A",
          "dcs_files": "MiG-29A",
          "liveries": ["mig-29a"],
          "core": "Bazar"
        },
        "mig-29c": {
          "names": ["mig-29c"],
          "friendly": "MiG-29C",
          "dcs_files": "MiG-29C",
          "liveries": ["mig-29c"],
          "core": "Bazar"
        },
        "p-47d": {
          "names": ["p-47d"],
          "friendly": "P-47D",
          "dcs_files": "P-47D Thunderbolt",
          "liveries": ["P-47D-30"],
          "core": "CoreMods/WWII Units/P-47D-30"
        },
        "p-51d": {
          "names": ["p-51d"],
          "friendly": "P-51D",
          "dcs_files": "P-51D Mustang",
          "liveries": ["P-51D"],
          "core": "CoreMods/WWII Units/P-51D"
        },
        "sa342": {
          "names": ["sa342"],
          "friendly": "SA342",
          "dcs_files": "SA342 Gazelle",
          "liveries": ["SA342L", "SA342M", "SA342Minigun", "SA342Mistral"],
          "core": "CoreMods/aircraft/SA342"
        },
        "spitfire lf mk ix": {
          "names": ["hawk", "hawk t.1a"],
          "friendly": "Spitfire LF Mk. IX",
          "dcs_files": "Spitfire LF Mk. IX",
          "liveries": ["SpitfireLFMkIX"],
          "core": "CoreMods/WWII Units/SpitfireLFMkIX"
        },
        "su-25": {
          "names": ["su-25"],
          "friendly": "Su-25",
          "dcs_files": "Su-25",
          "liveries": ["su-25"],
          "core": "Bazar"
        },
        "su-25t": {
          "names": ["su-25t"],
          "friendly": "Su-25T",
          "dcs_files": "Su-25T",
          "liveries": ["su-25t"],
          "core": "Bazar"
        },
        "su-27": {
          "names": ["su-27"],
          "friendly": "Su-27",
          "dcs_files": "Su-27",
          "liveries": ["su-27"],
          "core": "Bazar"
        },
        "su-33": {
          "names": ["su-33"],
          "friendly": "Su-33",
          "dcs_files": "Su-33",
          "liveries": ["su-33"],
          "core": "Bazar"
        },
        "uh-1h": {
          "names": ["uh-1h", "huey"],
          "friendly": "UH-1H",
          "dcs_files": "UH-1H Huey",
          "liveries": ["uh-1h"],
          "core": "Bazar"
        },
        "yak-52": {
          "names": ["yak-52"],
          "friendly": "Yak-52",
          "dcs_files": "Yak-52",
          "liveries": ["Yak-52"],
          "core": "CoreMods/aircraft/Yak-52"
        }
      }
    }

    # Copy the generic name of the unit to the config dict
    for type in self.Units.keys():
      for unit,config in self.Units[type].items():
        config['generic'] = unit

Units = UnitConfig()

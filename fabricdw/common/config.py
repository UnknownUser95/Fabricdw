from __future__ import annotations

import json
from enum import StrEnum
from os.path import exists, isdir
from typing import TypeVar

from colorama import Fore, Style

from fabricdw.common import absolute_path

CONFIG_FILE: str = absolute_path("~/.config/fabricdw.json")

_T = TypeVar("_T")


def _default_get(source: dict[str, _T], key: str, fallback: _T) -> _T:
	"""Get a value from a dict. Return fallback if key is not present"""
	return source[key] if key in source else fallback


class InstallationDoesNotExistError(Exception):
	def __init__(self, name: str):
		super().__init__(f"{Fore.RED}Installation '{name}' does not exist!{Style.RESET_ALL}")


class InstallationAlreadyExistError(Exception):
	def __init__(self, installation: Installation):
		super().__init__(
			f"{Fore.RED}Installation '{installation.pretty_name(Fore.RED)}' already exists ('{installation.root}')!"
			f"{Style.RESET_ALL}"
		)


class InvalidCombinationException(Exception):
	def __init__(self):
		super().__init__("Invalid combination of game, loader, and installer version!")


class VersionChoice(StrEnum):
	ASK = "ask"
	LATEST = "latest"


class DictSerialization:
	"""A class, which can be serialized and deserialized to and from a dict"""
	
	def to_dict(self) -> dict:
		"""Serialize to a dict"""
		pass
	
	@classmethod
	def from_dict(cls, data: dict) -> DictSerialization:
		"""Deserialize from a dict"""
		pass


class Installation(DictSerialization):
	def __init__(self, name: str, root: str):
		self.name = name
		self.root = root
	
	def __eq__(self, other):
		if isinstance(other, Installation):
			return other.name == self.name
		return False
	
	def __str__(self) -> str:
		return f"{self.pretty_name()} ({self.root})"
	
	@classmethod
	def from_dict(cls, data: dict) -> Installation:
		return cls(data["name"], data["root"])
	
	def to_dict(self) -> dict:
		return { 'root': self.root, 'name': self.name }
	
	def pretty_name(self, after: Fore = None) -> str:
		return Installation.pretty_name_str(self.name, after)
	
	@staticmethod
	def pretty_name_str(name: str, after: Fore = None) -> str:
		return f"{Fore.CYAN}{name}{Style.RESET_ALL}{after if after else ''}"
	
	@staticmethod
	def ensure_exists(name: str, remove_if_missing: bool = True) -> Installation:
		if ((installation := CONFIG.get_installation(name)) is None or not exists(installation.root) or not isdir(
			installation.root
		)):
			if remove_if_missing:
				CONFIG.remove_installation(Installation(name, ""))
			
			raise InstallationDoesNotExistError(name)
		
		return installation
	
	@staticmethod
	def ensure_does_not_exist(name: str) -> None:
		if (installation := CONFIG.get_installation(name)) is not None:
			raise InstallationAlreadyExistError(installation)


class Defaults(DictSerialization):
	def __init__(self, data: dict):
		self.min_ram = _default_get(data, "min-ram", 0.5)
		self.max_ram = _default_get(data, "max-ram", 6)
		self.idle_time = _default_get(data, "idle_time", 0)
		self.backups = _default_get(data, "backups", 5)
	
	@classmethod
	def from_dict(cls, data: dict) -> Defaults:
		return cls(data)
	
	def to_dict(self) -> dict:
		return {
			"min-ram": self.min_ram, "max-ram": self.max_ram, "idle_time": self.idle_time, "backups": self.backups
		}


class Config(DictSerialization):
	def __init__(self, default: Defaults, installations: list[Installation]):
		self.defaults: Defaults = default
		self.installations: list[Installation] = installations
	
	@classmethod
	def from_dict(cls, data: dict) -> Config:
		defaults = Defaults.from_dict(data['defaults'])
		installations = [Installation.from_dict(installation) for installation in data['installations']]
		
		return cls(defaults, installations)
	
	def to_dict(self) -> dict:
		return {
			'defaults': self.defaults.to_dict(),
			'installations': [installation.to_dict() for installation in self.installations]
		}
	
	def create_new_installation(self, name: str, root: str, print_message: bool = True) -> Installation:
		self.installations.append(
			installation := Installation(name, root)
		)
		
		if print_message:
			print(f"installation '{Installation.pretty_name_str(installation.name)}' created! ({installation.root})")
		
		return installation
	
	def remove_installation(self, installation: Installation) -> None:
		"""Removes the installation from the list of installations, however does not delete it."""
		self.installations.remove(installation)
	
	def get_installation(self, name: str) -> Installation | None:
		for installation in self.installations:
			if installation.name == name:
				return installation
		
		return None


def _load_config() -> Config:
	if exists(CONFIG_FILE):
		with open(CONFIG_FILE, 'r') as cfg:
			raw = json.load(cfg)
	else:
		print("config file missing, creating new")
		raw = { "defaults": { }, 'installations': [] }
	
	return Config.from_dict(raw)


CONFIG: Config = _load_config()


def write_config() -> None:
	with open(CONFIG_FILE, "w") as config:
		json.dump(CONFIG.to_dict(), config, indent=4)

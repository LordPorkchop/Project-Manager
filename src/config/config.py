from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

import win32file
import win32con

from src.common.exceptions import (
    ConfigNotParsedError,
    ConfigReadAccessDeniedError,
    ConfigWriteAccessDeniedError,
    MalformedConfigError,
    UnknownConfigKeyError,
)
from src.services.logger import get_logger as _get_logger

Scope = Literal["app", "user"]
Permission = Literal["read", "write"]


class Config:
    def __init__(
        self,
        path: Path | str = "config.cfg",
        parse_now: bool = True,
        lock_file: bool = False,
    ):
        self._scope: Scope = "app"
        self._logger = _get_logger("config")
        self._path = Path(path)
        self._config = {}
        self._meta = {}
        self._avail = False
        self._locked = False
        self._changed = False

        if lock_file:
            self.lock_file()

        if parse_now:
            self.parse()

        self._logger.debug("Config intialized")

    @property
    def available(self) -> bool:
        return self._avail

    @property
    def is_file_locked(self) -> bool:
        return self._locked

    def _get_entry(
        self, name: str, raise_errors: bool = False
    ) -> dict[str, Any] | None:
        if not self._avail:
            err_str = "Config has not been parsed yet, run 'parse' first"
            self._logger.error(err_str)
            if raise_errors:
                raise ConfigNotParsedError(err_str)
            return

        entry = self._config.get(name)
        if entry is None:
            err_str = f"'{name}' is not a valid config key"
            self._logger.error(err_str)
            if raise_errors:
                raise UnknownConfigKeyError(err_str)

        return entry

    def _check_access(
        self,
        name: str,
        entry: dict[str, Any],
        scope: Scope,
        requested_permission: Permission,
        raise_errors: bool = False,
    ) -> None:
        try:
            allowed = entry["permissions"][requested_permission][scope]
        except (KeyError, TypeError):
            err_str = f"Config entry '{name}' is corrupted"
            self._logger.error(err_str)
            if raise_errors:
                raise MalformedConfigError(err_str) from None

        if not isinstance(allowed, bool):
            err_str = f"Non-boolean permission value for {requested_permission}.{scope}"
            self._logger.error(err_str)
            if raise_errors:
                raise MalformedConfigError(err_str)
            else:
                return

        elif not allowed:
            err_str = f"Access denied: '{name}' is not {requested_permission}able for scope '{scope}'"
            self._logger.error(err_str)
            if raise_errors:
                if requested_permission == "read":
                    raise ConfigReadAccessDeniedError(err_str)
                else:  # requested permission is write
                    raise ConfigWriteAccessDeniedError(err_str)

    def _validate_value(
        self,
        name: str,
        entry: dict[str, Any],
        write_value: Any,
        raise_errors: bool = False,
    ):
        value_type_name = type(write_value).__name__
        self._logger.debug(
            f"Validating value of type {value_type_name} for config entry '{name}'"
        )

        if not entry:
            entry = self._get_entry(name) or {}
            if not entry:
                self._logger.error(
                    "Cannot validate value against empty entry, aborting"
                )
                if raise_errors:
                    raise ValueError("Cannot validate a value against empty entry")
                return

        expected = entry.get("type", "NotProvided")  # type null in config is semi-valid
        if expected == "NotProvided":
            self._logger.warning(
                f"Expected value type for entry '{name}' is not set, ignoring"
            )
            return

        elif expected == "literal":
            allowed_values = entry.get("possibleValues", [])
            if not allowed_values:
                self._logger.warning(
                    f"Expected type for entry '{name}' is set to 'Literal' but no values are allowed, ignoring"
                )
                return
            else:
                if write_value in allowed_values:
                    return
                else:
                    err_str = f"Write value for config entry '{name}' does not match allowed values"
                    self._logger.error(err_str)
                    if raise_errors:
                        raise TypeError(err_str)

        else:
            match expected:
                case "bool":
                    expected_type = bool
                case "float":
                    expected_type = float
                case "int":
                    expected_type = int
                case "str":
                    expected_type = str
                case "other":
                    self._logger.warning(
                        f"Expected value type for config entry '{name}' cannot be checked, skipping"
                    )
                    return
                case _:
                    self._logger.warning(
                        f"Unknown expected type '{expected}' for config entry '{name}', ignoring"
                    )
                    return

            if not isinstance(write_value, expected_type):
                err_str = f"Write value for config entry '{name}' must be '{expected_type.__name__}', not '{value_type_name}'"
                self._logger.error(err_str)
                if raise_errors:
                    raise TypeError(err_str)

    def set_scope(self, new_scope: Scope):
        self._scope = new_scope

    def read(self, config_key: str) -> Any:
        if config_key == "metadata":
            return self._get_entry(config_key, True)

        try:
            # vvvvv Will never be None, raises AttributeError instead
            entry: dict[str, Any] = self._get_entry(config_key, True)  # type: ignore
            self._check_access(config_key, entry, self._scope, "read", True)
            return entry.get("currentValue")
        except Exception:
            self._logger.exception(f"Cannot read from '{config_key}':")

    def get_metadata(self) -> dict[str, Any]:
        return dict(self._meta)

    def get_name(self) -> str:
        return self._name

    def get_version(self, verbose: bool = False):
        if verbose:
            return self._name + "Version" + self._version
        else:
            return self._version

    def get_repository(self) -> str:
        return self._repo_url

    def get_author(self) -> str:
        return self._author

    def write(self, config_key: str, value: Any) -> None:
        if config_key == "metadata":
            self._logger.error("Cannot write to metadata!")
            return

        try:
            entry: dict[str, Any] = self._get_entry(config_key, True)  # type: ignore
            self._check_access(config_key, entry, self._scope, "write", True)
            self._validate_value(config_key, entry, value, True)
            entry["currentValue"] = value
            self._changed = True
        except Exception:
            self._logger.exception(f"Cannot write to '{config_key}':")

    def parse(self, force: bool = False) -> None:
        if self._avail and not force:
            return

        self._logger.info("Parsing config...")

        try:
            with open(self._path, "r", encoding="utf-8") as file:
                self._config: dict[str, dict] = json.load(file) or {}
            self._meta: dict[str, str] = self._config["metadata"]
            self._version = self._meta["version"]
            self._name = self._meta["name"]
            self._repo_url = self._meta["repo"]
            self._author = self._meta["author"]

        except json.JSONDecodeError as e:
            self._logger.exception(f"Corrupted config file: {e}")
            raise MalformedConfigError("Config file is corrupted, see log") from None

        except KeyError:
            raise MalformedConfigError("Config metadata is missing or incomplete")

        else:
            self._avail = bool(self._config)

    def lock_file(self) -> Any:
        if self._locked:
            self._logger.error(
                "Attempted to lock config file though locked already, ignoring"
            )
            return self._handle
        h = win32file.CreateFile(
            str(self._path),
            win32con.GENERIC_READ | win32con.GENERIC_WRITE,
            0,  # no sharing
            None,
            win32con.OPEN_EXISTING,
            win32con.FILE_ATTRIBUTE_NORMAL,
            None,
        )
        self._locked = True
        self._logger.info("Config file locked")
        self._handle = h
        return h

    def unlock_file(self) -> None:
        if self._locked:
            win32file.CloseHandle(self._handle)  # type: ignore
            self._locked = False
            self._logger.info("Config file unlocked")
        else:
            self._logger.error(
                "Attempted to unlock config file though not locked, ignoring"
            )

    def close(self):
        self._logger.info("Closing config...")
        self.save()
        if self._locked:
            self.unlock_file()

    def __del__(self):
        self.close()

    def __enter__(self) -> Config:
        self._logger.info("New instance initialized via context manager")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        self._logger.info("Exited context manager instance")

    def __getattr__(self, name: str) -> Any:
        return self.read(name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_"):  # in-class access
            object.__setattr__(self, name, value)
            return

        self.write(name, value)

    def save(self):
        self._logger.info(f"Saving config to '{self._path}'...")
        if self._changed:
            self._logger.debug(f"Saving config to {self._path}")
            with open(self._path, "w", encoding="utf-8") as cfgfile:
                json.dump(self._config, cfgfile, indent=4)
            self._logger.info("Config saved successfully")
            self._changed = False
        else:
            self._logger.info("Skipped config save as no changes were made")


_CONFIG_FILE_PATH = Path("./config.cfg").absolute()
_CONFIG_INSTANCE: Config | None = None


def get_config(lock_file: bool = False) -> Config:
    global _CONFIG_INSTANCE
    if _CONFIG_INSTANCE is None:
        _CONFIG_INSTANCE = Config(_CONFIG_FILE_PATH, lock_file=lock_file)
    return _CONFIG_INSTANCE

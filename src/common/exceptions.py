# FROM src/config/config.py
class ConfigNotParsedError(Exception):
    pass


class ConfigReadAccessDeniedError(Exception):
    pass


class ConfigWriteAccessDeniedError(Exception):
    pass


class MalformedConfigError(Exception):
    pass


class UnknownConfigKeyError(Exception):
    pass

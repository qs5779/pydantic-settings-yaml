from os import path
from typing import Dict

from pydantic import BaseModel
from pydantic_settings import SettingsConfigDict
from yaml_settings_pydantic import BaseYamlSettings


class MySettings(BaseYamlSettings):
    """Example settings.

    :class MyDataBaseSettings: Schema for the nested field.
    :attr myFirstSettings: A scalar field.
    :attr myDatabaseSettings: A nested field.
    """

    model_config = SettingsConfigDict(
        env_prefix="MY_SETTINGS_",
        env_nested_delimiter="__",
    )

    # Dunders implement which files will be used and how.
    # This one specifies the files to be used. Multiple files can be used.
    # Make sure that this is a tuple.
    __yaml_files__ = (path.realpath(path.join(path.dirname(__file__), "example.yaml")),)

    # Use reload to determine if CreateYamlSettings will load and parse the
    # provided files every time it is called.
    __yaml_reload__ = True

    # Nested configuration example.
    class MyDataBaseSettings(BaseModel):
        "Dummy schema for nested."

        class MyNestedDatabaseSettings(BaseModel):
            "Second order nested schema."
            host: str
            port: int
            username: str
            password: str

        connectionspec: Dict[str, str]
        hostspec: MyNestedDatabaseSettings

    # Configuration fields.
    myFirstSetting: int
    myDatabaseSettings: MyDataBaseSettings

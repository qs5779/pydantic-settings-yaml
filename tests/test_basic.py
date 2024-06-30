import logging
import os
import pathlib
from typing import Annotated, Set, Tuple, Type
from unittest import mock

import pytest
import yaml
from pydantic import BaseModel
from pydantic.fields import Field

from yaml_settings_pydantic import (
    DEFAULT_YAML_FILE_CONFIG_DICT,
    BaseYamlSettings,
    CreateYamlSettings,
    YamlFileConfigDict,
    YamlSettingsConfigDict,
    resolve_filepaths,
)

# logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.DEBUG)


class TestCreateYamlSettings:
    def test_reload(self, fileDummies):
        # Test args
        with pytest.raises(ValueError):
            CreateYamlSettings(BaseYamlSettings)

        # Make sure it works. Check name of returned learcal
        def create_settings(reload=None, files=None):
            return type(
                "Settings",
                (BaseYamlSettings,),
                dict(
                    __yaml_reload__=reload or False,
                    __yaml_files__=files or set(fileDummies),
                ),
            )

        Settings = create_settings()
        yaml_settings = CreateYamlSettings(Settings)
        yaml_settings()
        assert not yaml_settings.reload

        # NOTE: Malform a file.
        bad = Settings.__yaml_files__.pop()
        with open(bad, "w") as file:
            yaml.dump([], file)

        # # NOTE: Loading should not be an error as the files should not be reloaded.
        # yaml_settings()
        #
        # # NOTE: Test reloading with bad file.
        # #       This could be called without the args as mutation is visible
        # #       to fn.
        # Settings = create_settings(reload=False)
        # yaml_settings = CreateYamlSettings(Settings)
        #
        # with pytest.raises(ValueError) as err:
        #     yaml_settings()
        #
        # assert str(bad) in str(err.value)
        #
        # with open(bad, "w") as file:
        #     yaml.dump({}, file)
        #
        # yaml_settings()

    def from_model_config(
        self, **kwargs
    ) -> Tuple[CreateYamlSettings, Type[BaseYamlSettings]]:
        Settings = type(
            "Settings",
            (BaseYamlSettings,),
            dict(model_config=YamlSettingsConfigDict(**kwargs)),
        )
        return CreateYamlSettings(Settings), Settings

    def test_dunders_have_priority(self) -> None:
        init_reload = True
        yaml_settings, Settings = self.from_model_config(
            yaml_files={"foo-bar.yaml"},
            yaml_reload=init_reload,
        )

        default = DEFAULT_YAML_FILE_CONFIG_DICT
        assert yaml_settings.files == {"foo-bar.yaml": default}
        assert yaml_settings.reload == init_reload

        final_files: Set[str] = {"spam-eggs.yaml"}
        OverwriteSettings = type(
            "OverwriteSettings",
            (Settings,),
            dict(__yaml_files__=final_files),
        )
        yaml_settings = CreateYamlSettings(OverwriteSettings)

        assert yaml_settings.files == {"spam-eggs.yaml": default}
        assert yaml_settings.reload == init_reload

    @pytest.mark.parametrize(
        "yaml_files",
        [
            "foo.yaml",
            {"foo.yaml"},
            {"foo.yaml": YamlFileConfigDict(required=True, subpath=None)},
        ],
    )
    def test_hydration_yaml_files(self, yaml_files) -> None:
        make, _ = self.from_model_config(yaml_files=yaml_files)

        assert len(make.files) == 1
        assert isinstance(make.files, dict)
        assert (foo := make.files.get("foo.yaml")) is not None
        assert isinstance(foo, dict)
        assert foo.get("required") is True
        assert foo.get("subpath") is None

    def test_yaml_not_required(self) -> None:
        # Should not raise error
        make, Settings = self.from_model_config(
            yaml_files={
                "foo.yaml": YamlFileConfigDict(
                    required=False,
                    subpath=None,
                )
            }
        )
        assert make.files.get("foo.yaml")
        make.load()

        # Should raise error
        make, _ = self.from_model_config(yaml_files="foo.yaml")
        with pytest.raises(ValueError) as err:
            make.load()

        assert str(err.value)

    def test_envvar(self, tmp_path: pathlib.Path) -> None:

        # ------------------------------------------------------------------- #
        # NOTE: Settup

        path_default = str(tmp_path / "default.yaml")
        path_other = str(tmp_path / "other.yaml")

        make, _Settings = self.from_model_config(
            yaml_files={
                path_default: YamlFileConfigDict(
                    envvar="FOO_PATH",
                    required=False,
                    subpath=None,
                )
            }
        )
        assert set(make.files.keys()) == {path_default}

        class SettingsModel(BaseModel):
            whatever: Annotated[str, Field(default="whatever")]

        class Settings(SettingsModel, _Settings): ...

        default = SettingsModel(whatever="default")  # type: ignore
        other = SettingsModel(whatever="other")  # type: ignore

        with open(path_default, "w") as file_default, open(
            path_other, "w"
        ) as file_other:
            yaml.dump(default.model_dump(mode="json"), file_default)
            yaml.dump(other.model_dump(mode="json"), file_other)

        # ------------------------------------------------------------------- #
        # NOTE: Actual tests.

        with mock.patch.dict(os.environ, {"FOO_PATH": path_other}, clear=True):
            filepath_resolved = resolve_filepaths(
                path_default,
                make.files[path_default],
            )
            assert filepath_resolved == path_other

            # NOTE: Now testing loading.
            settings = Settings()
            assert settings.whatever == "other"

        with mock.patch.dict(os.environ, {"FOO_PATH": ""}, clear=True):
            filepath_resolved = resolve_filepaths(
                path_default,
                make.files[path_default],
            )
            assert filepath_resolved == path_default

            settings = Settings()
            assert settings.whatever == "default"

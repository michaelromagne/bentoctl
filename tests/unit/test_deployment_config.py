# pylint: disable=W0621
from pathlib import Path

import pytest

from bentoctl import deployment_config as dconf
from bentoctl.exceptions import DeploymentConfigNotFound, InvalidDeploymentConfig
from bentoctl.operator.operator import _import_module
from tests.conftest import TESTOP_PATH


def assert_no_help_message_in_schema(schema):
    for _, rules in schema.items():
        assert "help_message" not in rules
        if rules["type"] == "dict":
            assert_no_help_message_in_schema(rules["schema"])
        elif rules["type"] == "list":
            assert_no_help_message_in_schema({"list_item": rules["schema"]})


def test_remove_help_message():
    operator_config = _import_module("operator_config", TESTOP_PATH)
    schema = operator_config.OPERATOR_SCHEMA
    schema_without_help_msg = dconf.remove_help_message(schema)
    assert_no_help_message_in_schema(schema_without_help_msg)


def test_deployment_config_init(get_mock_operator_registry, monkeypatch):
    # empty deployment_config
    with pytest.raises(InvalidDeploymentConfig):
        dconf.DeploymentConfig({})

    # deployment_config with incorrect api_version
    with pytest.raises(InvalidDeploymentConfig):
        dconf.DeploymentConfig({"api_version": "v1"})

    # deployment_config with no deployment name
    with pytest.raises(InvalidDeploymentConfig):
        dconf.DeploymentConfig({"api_version": "v1", "spec": {}})

    # deployment_config with operator that is not installed
    monkeypatch.setattr(dconf, "local_operator_registry", get_mock_operator_registry)
    with pytest.raises(InvalidDeploymentConfig):
        dconf.DeploymentConfig(
            {
                "api_version": "v1",
                "name": "test",
                "template": "terraform",
                "operator": "testop",
                "spec": {},
            }
        )

    # deployment_config with no template
    with pytest.raises(InvalidDeploymentConfig):
        dconf.DeploymentConfig(
            {
                "api_version": "v1",
                "name": "test",
                "template": "",
                "operator": "testop",
                "spec": {},
            }
        )

    # deployment_config with invalid template
    with pytest.raises(InvalidDeploymentConfig):
        dconf.DeploymentConfig(
            {
                "api_version": "v1",
                "name": "test",
                "template": "not-valid-template",
                "operator": "testop",
                "spec": {},
            }
        )


VALID_YAML = """
api_version: v1
name: test
operator: testop
template: terraform
spec:
    project_id: testproject
    instances:
        min: 1
        max: 2
"""
INVALID_YAML = """
api_version: tst: something: something
"""
VALID_YAML_INVALID_SCHEMA = """
api_version: v1
name: test
operator: testop
template: terraform
spec:
    project_id: testproject
"""


def create_yaml_file(yml_str, path):
    with open(Path(path, "deployment_config.yaml"), "w", encoding="utf-8") as f:
        f.write(yml_str)


@pytest.fixture
def op_reg_with_testop(get_mock_operator_registry, monkeypatch):
    monkeypatch.setattr(dconf, "local_operator_registry", get_mock_operator_registry)
    get_mock_operator_registry.add(TESTOP_PATH)

    yield get_mock_operator_registry


def test_deployment_config_from_file(
    tmp_path, op_reg_with_testop, tmp_bento_path
):  # pylint: disable=W0613
    with pytest.raises(DeploymentConfigNotFound):
        dconf.DeploymentConfig.from_file(tmp_path / "nofile.yaml")

    create_yaml_file(INVALID_YAML, tmp_path)
    with pytest.raises(InvalidDeploymentConfig):
        dconf.DeploymentConfig.from_file(tmp_path / "deployment_config.yaml")

    create_yaml_file(VALID_YAML, tmp_path)
    assert dconf.DeploymentConfig.from_file(tmp_path / "deployment_config.yaml")


def test_validate_operator_config(
    op_reg_with_testop, tmp_bento_path
):  # pylint: disable=W0613
    import yaml

    dconf.DeploymentConfig(yaml.safe_load(VALID_YAML))

    with pytest.raises(InvalidDeploymentConfig):
        dconf.DeploymentConfig(yaml.safe_load(VALID_YAML_INVALID_SCHEMA))
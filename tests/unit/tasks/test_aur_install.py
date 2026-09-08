from unittest.mock import Mock, call

import pytest

from phs.tasks.aur_install import AurInstall
from phs.template import TemplateRenderer


@pytest.mark.parametrize("packages", [(), ("yay",), ("yay", "example-git")])
def test_renders_and_runs_each_package_in_order(target, packages):
    renderer = Mock(spec=TemplateRenderer)
    scripts = [f"install {package}\n" for package in packages]
    renderer.render.side_effect = scripts
    AurInstall(packages, renderer).execute(target)
    assert renderer.render.call_args_list == [
        call("scripts/install_aur_package.sh.j2", package=package)
        for package in packages
    ]
    assert target.runner.run.call_args_list == [
        call(["bash", "-s"], input_text=script) for script in scripts
    ]

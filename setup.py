#!/usr/bin/env python3


import os
import platform
import shutil
import stat
import sys
from distutils.command.build import build as orig_build
from distutils.core import Command
from pathlib import Path

from setuptools import setup
from setuptools.command.install import install as orig_install

SHFMT_VERSION = "3.10.0"


class build(orig_build):
    sub_commands = orig_build.sub_commands + [("fetch_executables", None)]


class install(orig_install):
    sub_commands = orig_install.sub_commands + [("install_executable", None)]


class fetch_executables(Command):
    build_temp = None

    def initialize_options(self):
        pass

    def finalize_options(self):
        self.set_undefined_options("build", ("build_temp", "build_temp"))

    def run(self):
        # Save executable to self.build_temp
        Path(self.build_temp).mkdir(parents=True, exist_ok=True)
        self._copy_executable()

    def _copy_executable(self):
        orig_exe_path = self._get_executable_path()

        exe_name = "shfmt" if sys.platform not in ("win32", "cygwin") else "shfmt.exe"
        exe_path = Path(self.build_temp) / exe_name
        Path(self.build_temp).mkdir(parents=True, exist_ok=True)

        shutil.copyfile(str(orig_exe_path), str(exe_path))

        # Mark as executable.
        # https://stackoverflow.com/a/14105527
        mode = os.stat(str(exe_path)).st_mode
        mode |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        os.chmod(str(exe_path), mode)

    def _get_executable_path(self):
        executables = Path(__file__).parent.resolve() / "executables"
        sys_platform = sys.platform
        platform_machine = platform.machine()

        if sys_platform == "darwin":
            if platform_machine == "x86_64":
                platform_machine = "amd64"
        elif sys_platform == "linux":
            if platform_machine in ("i386", "i686"):
                platform_machine = "386"
            elif platform_machine == "x86_64":
                platform_machine = "amd64"
            elif platform_machine in ("armv6hf", "armv7l"):
                platform_machine = "arm"
            elif platform_machine == "aarch64":
                platform_machine = "arm64"
        elif sys_platform in ("win32", "cygwin"):
            sys_platform = "windows"
            if platform_machine in ("x86", "i386"):
                platform_machine = "386"
            elif platform_machine == "AMD64" or platform_machine == "x86_64":
                platform_machine = "amd64"

        if (executables / f"shfmt_v{SHFMT_VERSION}_{sys_platform}_{platform_machine}").exists():
            return executables / f"shfmt_v{SHFMT_VERSION}_{sys_platform}_{platform_machine}"
        elif (executables / f"shfmt_v{SHFMT_VERSION}_{sys_platform}_{platform_machine}.exe").exists():
            return executables / f"shfmt_v{SHFMT_VERSION}_{sys_platform}_{platform_machine}.exe"
        else:
            raise RuntimeError(f"Unsupported platform: {sys_platform} {platform_machine}")


class install_executable(Command):
    description = "install the executable"
    outfiles = ()
    build_dir = install_dir = None

    def initialize_options(self):
        pass

    def finalize_options(self):
        # this initializes attributes based on other commands' attributes
        self.set_undefined_options("build", ("build_temp", "build_dir"))
        self.set_undefined_options("install", ("install_scripts", "install_dir"))

    def run(self):
        self.outfiles = self.copy_tree(self.build_dir, self.install_dir)

    def get_outputs(self):
        return self.outfiles


cmdclass = {
    "install": install,
    "install_executable": install_executable,
    "build": build,
    "fetch_executables": fetch_executables,
}


try:
    from wheel.bdist_wheel import bdist_wheel as orig_bdist_wheel
except ImportError:
    pass
else:

    class bdist_wheel(orig_bdist_wheel):
        def finalize_options(self):
            orig_bdist_wheel.finalize_options(self)
            # Mark us as not a pure python package
            self.root_is_pure = False

        def get_tag(self):
            _, _, plat = orig_bdist_wheel.get_tag(self)
            # We don't contain any python source, nor any python extensions
            return "py2.py3", "none", plat

    cmdclass["bdist_wheel"] = bdist_wheel


setup(cmdclass=cmdclass)

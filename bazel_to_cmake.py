#!/usr/bin/env python
# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A script to convert Bazel build systems to CMakeLists.txt.

See README.md for more information.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import glob
import os
import sys
import textwrap
import requests
from converter import Converter
import git
import wget
import tarfile

def StripColons(deps):
  return map(lambda x: x[1:], deps)

def IsSourceFile(name):
  return name.endswith(".c") or name.endswith(".cc")

data = {}
interpreter_curdir = [os.curdir]

def GetDict(obj):
    ret = {}
    for k in dir(obj):
        if not k.startswith("_"):
            ret[k] = getattr(obj, k)
    return ret


class BuildFileFunctions(object):
    def __init__(self, converter):
        self.converter = converter
        self._subprojects = []

    def _add_deps(self, kwargs, keyword=""):
        if "deps" not in kwargs:
            return
        self.converter.toplevel += "target_link_libraries(%s%s\n  %s)\n" % (
            kwargs["name"],
            keyword,
            "\n  ".join(StripColons(kwargs["deps"]))
        )

    def attr(self, *args):
        print(args)
        assert False, "Failed to load attr"

    def load(self, *args, **kwargs):
        if kwargs != {}:
            print(kwargs)
            return

        url = args[0]
        print("Fetching URL: " + url)
        if url.startswith("@bazel_tools"):
            return
            bazel_src = os.path.join(interpreter_curdir[-1], "bazel")
            if not os.path.exists(bazel_src):
                os.makedirs(bazel_src, exist_ok = True)
                bazel_tools_repo = "https://github.com/bazelbuild/bazel.git"
                git.Git(os.curdir).clone(bazel_tools_repo)
            file_path, bazel_file = url.split("//")[1].split(":")
            interpreter_curdir.append(os.path.join(bazel_src, file_path))
            load_bazel_file(self.converter, os.path.join(bazel_src, file_path, bazel_file))
            interpreter_curdir.pop()
        elif url.startswith(":"):
            # Local file, do nothing
            bazel_file = url.replace(":", "")
            load_bazel_file(self.converter, os.path.join(interpreter_curdir[-1], bazel_file))
            print("Finished loading file")
        elif url.startswith("//closure"):
            # Skip closure defs
            return
            closure_src = os.path.join(interpreter_curdir[-1], "closure")
            if not os.path.exists(closure_src):
                os.makedirs(closure_src, exist_ok = True)
                bazel_closure_repo = "https://github.com/bazelbuild/rules_closure.git"
                git.Git(interpreter_curdir[-1]).clone(bazel_closure_repo)

            load_bazel_file(self.converter, os.path.join(closure_src, "BUILD"))

    def cc_library(self, **kwargs):
        if kwargs["name"] == "amalgamation" or kwargs["name"] == "upbc_generator":
            return
        files = kwargs.get("srcs", []) + kwargs.get("hdrs", [])

        if filter(IsSourceFile, files):
            # Has sources, make this a normal library.
            self.converter.toplevel += "add_library(%s\n  %s)\n" % (
                kwargs["name"],
                "\n  ".join(files)
            )
            self._add_deps(kwargs)
        else:
            # Header-only library, have to do a couple things differently.
            # For some info, see:
            #  http://mariobadr.com/creating-a-header-only-library-with-cmake.html
            self.converter.toplevel += "add_library(%s INTERFACE)\n" % (
              kwargs["name"]
            )
            self._add_deps(kwargs, " INTERFACE")

    def cc_binary(self, **kwargs):
        pass

    def cc_test(self, **kwargs):
        # Disable this until we properly support upb_proto_library().
        # self.converter.toplevel += "add_executable(%s\n  %s)\n" % (
        #     kwargs["name"],
        #     "\n  ".join(kwargs["srcs"])
        # )
        # self.converter.toplevel += "add_test(NAME %s COMMAND %s)\n" % (
        #     kwargs["name"],
        #     kwargs["name"],
        # )

        # if "data" in kwargs:
        #   for data_dep in kwargs["data"]:
        #     self.converter.toplevel += textwrap.dedent("""\
        #       add_custom_command(
        #           TARGET %s POST_BUILD
        #           COMMAND ${CMAKE_COMMAND} -E copy
        #                   ${CMAKE_SOURCE_DIR}/%s
        #                   ${CMAKE_CURRENT_BINARY_DIR}/%s)\n""" % (
        #       kwargs["name"], data_dep, data_dep
        #     ))

        # self._add_deps(kwargs)
        assert False, "Failed to test"

    def py_library(self, **kwargs):
        assert False, "Failed to pylibrary"

    def py_binary(self, **kwargs):
        assert False, "Failed to pybinary"

    def closure_repositories(self, **kwargs):
        pass

    def lua_cclibrary(self, **kwargs):
        assert False, "Failed to lua_cclibrary"

    def lua_library(self, **kwargs):
        assert False, "Failed to lua_library"

    def lua_binary(self, **kwargs):
        assert False, "Failed to lua_binary"

    def lua_test(self, **kwargs):
        assert False, "Failed to lua_test"

    def sh_test(self, **kwargs):
        assert False, "Failed to sh_test"

    def make_shell_script(self, **kwargs):
        assert False, "Failed to make shell script"

    def exports_files(self, files, **kwargs):
        for f in files:
            if f.endswith(".bzl"):
                load_bazel_file(self.converter, os.path.join(interpreter_curdir[-1], f))
        # assert False, "Failed to make export files"

    def filegroup(self, **kwargs):
        # print(kwargs)
        return

    def proto_library(self, **kwargs):
        assert False, "Failed to make proto library"

    def generated_file_staleness_test(self, **kwargs):
        assert False, "Failed to make generate staleness test"

    def upb_amalgamation(self, **kwargs):
        assert False, "Failed to make upb amalgamation"

    def upb_proto_library(self, **kwargs):
        assert False, "Failed to make upb proto"

    def upb_proto_reflection_library(self, **kwargs):
        assert False, "Failed to make upb reflection"

    def java_import_external(self, **kwargs):
        # print(kwargs)
        return

    def skylark_library(self, **kwargs):
        return
        print(kwargs)
        name = kwargs.get("name")
        lib = kwargs.get("lib")
        srcs = kwargs.get("src")
        deps = kwargs.get("deps")

        for d in deps:
            d_dir, d_file = d.replace("//", "").split(":")
            load_bazel_file(self.converter, os.path.join(interpreter_curdir[-1], d_dir, d_file))
        b_dir, b_file = srcs.replace("//", "").split(":")
        load_bazel_file(self.converter, os.path.join(interpreter_curdir[-1], b_dir, bfile))

        assert False

    def genrule(self, **kwargs):
        assert False, "Failed to genrule"

    def config_setting(self, **kwargs):
        assert False, "Failed to config_setting"

    def select(self, arg_dict):
        assert False, "Failed to select"
        return []

    def glob(self, *args):
        pattern = args[0]
        assert len(pattern) == 1
        return list(glob.glob(os.path.join(interpreter_curdir[-1], pattern[0])))

    def licenses(self, *args):
        # assert False, "Failed to licenses"
        pass

    def package(self, **kwargs):
        default_visibility = kwargs.get("default_visibility", "//visibility:public")

    def map_dep(self, arg):
        assert False, "Failed to map_dep"
        return arg

    def bazel_toolchains_repositories(self, **kwargs):
        print(kwargs)
        return

    def container_repositories(self, **kwargs):
        print(kwargs)
        return

    def remote_config_workspace(self, **kwargs):
        print(kwargs)

    def swift_rules_dependencies(self, **kwargs):
        print(kwargs)

    def check_bazel_version_at_least(self, *args, **kwargs):
        print(*args, kwargs)

    def android_configure(self, **kwargs):
        print(kwargs)

    def android_workspace(self, **kwargs):
        print(kwargs)

    def tf_bind(self, **kwargs):
        print(kwargs)

    def bazel_toolchains_archive(self, **kwargs):
        print(kwargs)
        return

    def register_toolchains(self, *args, **kwargs):
        print(args, kwargs)
        return

    def tf_repositories(self, **kwargs):
        print(kwargs)
        return

class WorkspaceFileFunctions(BuildFileFunctions):
    def __init__(self, converter):
        self.converter = converter

    """
    def load(self, *args):
        url = args[0]
        print("Fetching URL: " + url)
        if url.startswith("@bazel_tools"):
            return
            bazel_src = os.path.join(os.curdir, "bazel")
            if not os.path.exists(bazel_src):
                os.makedirs(bazel_src, exist_ok = True)
                bazel_tools_repo = "https://github.com/bazelbuild/bazel.git"
                git.Git(os.curdir).clone(bazel_tools_repo)
            load_dir, load_file = url.split("//")[1].split(":")
            bazel_file = load_file.replace(":", "/")

            file_path = os.path.join(bazel_src, load_dir)

            interpreter_curdir.append(file_path)
            load_bazel_file(self.converter, os.path.join(file_path, bazel_file))
            interpreter_curdir.pop()
        elif url.startswith("//closure"):
            # Skip closure defs
            closure_src = os.path.join(interpreter_curdir[-1], "closure")
            if not os.path.exists(closure_src):
                os.makedirs(closure_src, exist_ok = True)
                bazel_closure_repo = "https://github.com/bazebuild/rules_closure.git"
                git.Git(interpreter_curdir[-1]).clone(bazel_closure_repo)
            subproject = load_subproject(closure_src)
            self.converter._subprojects(subproject)
        else:
            print(args)
            assert False, "Failed to load"
    """

    def workspace(self, **kwargs):
        self.converter.prelude += "project(%s)\n" % (kwargs["name"])


    def http_archive(self, **kwargs):
        name = kwargs.get("name")
        urls = kwargs.get("urls")
        strip_prefix = kwargs.get("strip_prefix")
        print("Fetching: " + name)
        dest_dir = os.path.join(interpreter_curdir[-1], name)
        extracted_dir = os.path.join(dest_dir, strip_prefix)
        for url in urls:
            filename = url.split("/")[-1]
            if not os.path.exists(os.path.join(dest_dir, strip_prefix)):
                os.makedirs(dest_dir, exist_ok = True)
                try:
                    wget.download(url, out = os.path.join(dest_dir, filename))

                    # Extract
                    if filename.endswith("tar.gz"):
                        print("Extracting tar")
                        tf = tarfile.open(os.path.join(dest_dir, filename))
                        tf.extractall(path = dest_dir)
                        break
                except:
                    print("Failed to get repository")

        if os.path.exists(os.path.join(extracted_dir, "WORKSPACE")):
            interpreter_curdir.append(extracted_dir)
            subproject = load_subproject(proj_dir = extracted_dir)
            self.converter.add_subproject(subproject)
            interpreter_curdir.pop()
        elif os.path.exists(os.path.join(extracted_dir, "BUILD")):
            load_bazel_file(self.converter, os.path.join(extracted_dir, "BUILD"))
        elif os.path.exists(os.path.join(extracted_dir, "CMakeLists.txt")):
            print("Found CMake Project!")
        else:
            assert False, "Failed to get repository"

    def git_repository(self, **kwargs):
        assert False, "Failed to get git repository"

converter = Converter(os.curdir)
globs = GetDict(Converter)

def load_bazel_file(converter, filename):
    with open(filename, "r") as f:
        print("Reading file" + filename)
        exec(f.read(), GetDict(BuildFileFunctions(converter)), globs)

def load_subproject(proj_dir):
    new_conv = Converter(proj_dir)
    with open(os.path.join(proj_dir, "WORKSPACE"), "r") as f:
        exec(f.read(), GetDict(WorkspaceFileFunctions(new_conv)), globs)
    load_bazel_file(new_conv, os.path.join(proj_dir, "BUILD"))
    return new_conv

load_subproject(os.curdir)
#with open("WORKSPACE", "r") as workspace:
#    exec(workspace.read(), GetDict(WorkspaceFileFunctions(converter)))
#with open("BUILD", "r") as workspace:
#    exec(build.read(), GetDict(BuildFileFunctions(converter)))

with open(sys.argv[1], "w") as f:
  f.write(converter.convert())

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
import zipfile

def StripColons(deps):
  return map(lambda x: x[1:], deps)

def IsSourceFile(name):
  return name.endswith(".c") or name.endswith(".cc")

data = {}
interpreter_curdir = [os.curdir]

def GetDict(obj):
    ret = {}
    for k in dir(obj):
        if not k.startswith("__"):
            ret[k] = getattr(obj, k)
    return ret

loaded_projects = {}

class BuildFileFunctions(object):
    class struct:
        def __init__(self, *args, **kwargs):
            self.after_each = kwargs.get("after_each")
            self.before_each = kwargs.get("before_each")
            self.uniq = kwargs.get("uniq")

    class attr:
        def label_list(*args, **kwargs):
            allow_files = kwargs.get("allow_files")

        def int(*args, **kwargs):
            doc = kwargs.get("doc", "")

        def string(*args, **kwargs):
            doc = kwargs.get("doc", "")

        def string_list(*args, **kwargs):
            doc = kwargs.get("doc", "")

        def string_dict(*args, **kwargs):
            doc = kwargs.get("doc", "")

        def label(*args, **kwargs):
            doc = kwargs.get("doc", "")

        def bool(*args, **kwargs):
            doc = kwargs.get("doc", "")
            #print(args, kwargs)
            #assert False

    def __init__(self, converter):
        self.converter = converter
        self._subprojects = []

    def _go_repository(self, *args, **kwargs):
        print(args, kwargs)
        assert False

    def _git_repository(self, *args, **kwargs):
        print(args, kwargs)
        assert False

    def _http_archive(self, *args, **kwargs):
        print(args, kwargs)
        assert False

    def _gazelle_binary(self, *args, **kwargs):
        print(args, kwargs)
        assert False

    def Label(self, *args, **kwargs):
        #print(args, kwargs)
        pass

    def depset(self, *args, **kwargs):
        print(args, kwargs)
        # assert False


    def __add_deps(self, kwargs, keyword=""):
        if "deps" not in kwargs:
            return
        self.converter.toplevel += "target_link_libraries(%s%s\n  %s)\n" % (
            kwargs["name"],
            keyword,
            "\n  ".join(StripColons(kwargs["deps"]))
        )

    def gazelle(self, *args, **kwargs):
        name = kwargs.get("name")

    def buildifier(self, *args, **kwargs):
        name = kwargs.get("name")

    def rules_cc_deps(self, *args, **kwargs):
        pass

    def rules_cc_setup(self, *args, **kwargs):
        pass

    def rules_cc_internal_deps(self, *args, **kwargs):
        pass

    def rules_cc_internal_setup(self, *args, **kwargs):
        pass

    def rules_proto_dependencies(self, *args, **kwargs):
        pass

    def rules_proto_toolchains(self, *args, **kwargs):
        pass

    def rules_docker_toolchains(self, *args, **kwargs):
        pass

    def docker_toolchain_configure(self, *args, **kwargs):
        pass

    def container_repositories(self, *args, **kwargs):
        pass

    def container_deps(self, *args, **kwargs):
        pass

    def container_go_deps(self, *args, **kwargs):
        pass

    def bazel_toolchains_images(self, *args, **kwargs):
        pass

    def bazel_toolchains_go_deps(self, *args, **kwargs):
        pass

    def container_pull(self, *args, **kwargs):
        pass

    def http_file(self, *args, **kwargs):
        pass

    def gcs_file(self, *args, **kwargs):
        pass

    def load(self, *args, **kwargs):
        print(args, kwargs)
        if len(args) < 2:
            print("Skipping invalid load: " + str(args) + " " + str(kwargs))
            return
        url = args[0]
        name = args[1]
        print("Loading: " + str(args) + " " + str(kwargs))
        if url.startswith("@bazel_tools"):
            return
            print("Fetching URL: " + url)
            bazel_src = os.path.abspath(os.path.join(interpreter_curdir[-1], "bazel"))
            if not os.path.exists(bazel_src):
                os.makedirs(bazel_src, exist_ok = True)
                bazel_tools_repo = "https://github.com/bazelbuild/bazel.git"
                git.Git(interpreter_curdir[-1]).clone(bazel_tools_repo)
            file_path, bazel_file = url.split("//")[1].split(":")
            interpreter_curdir.append(os.path.abspath(os.path.join(bazel_src, file_path)))
            load_bazel_file(self.converter, os.path.join(bazel_src, file_path, bazel_file))
            interpreter_curdir.pop()
        elif url.startswith("@io_bazel"):
            return
        elif url.startswith("@"):
            if url.startswith("@com_github"):
                print("Fetching URL: " + url)
                project_split = url.split("//")[0].split("_")
                github_user = project_split[2]
                github_repo = project_split[3]
                bazel_src = os.path.abspath(os.path.join(interpreter_curdir[-1], github_repo))
                bazel_url_repo = "https://github.com/"+github_user+"/"+github_repo+".git"
            else:
                print("Fetching URL: " + url)
                if url.startswith("@rules"):
                    # Rules repos use underscores, not hyphens
                    bazel_repo = url.replace("@", "").split("//")[0]
                else:
                    bazel_repo = url.replace("@", "").replace("_", "-").split("//")[0]
                bazel_src = os.path.abspath(os.path.join(interpreter_curdir[-1], bazel_repo))
                bazel_url_repo = "https://github.com/bazelbuild/"+bazel_repo+".git"

            if not os.path.exists(bazel_src):
                os.makedirs(bazel_src, exist_ok = True)
                git.Git(interpreter_curdir[-1]).clone(bazel_url_repo)
            file_path, bazel_file = url.split("//")[1].split(":")
            interpreter_curdir.append(os.path.abspath(os.path.join(bazel_src, file_path)))
            load_bazel_file(self.converter, os.path.join(bazel_src, file_path, bazel_file))
            interpreter_curdir.pop()

        elif url.startswith(":"):
            if name not in loaded_projects.keys():
                loaded_projects.update({name: None})
                # Local file, do nothing
                bazel_file = url.replace(":", "")
                load_bazel_file(self.converter, os.path.abspath(os.path.join(interpreter_curdir[-1], bazel_file)))
        elif url.startswith("//closure"):
            # Skip closure defs
            return
            closure_src = os.path.abspath(os.path.join(interpreter_curdir[-1], "closure"))
            if not os.path.exists(closure_src):
                os.makedirs(closure_src, exist_ok = True)
                bazel_closure_repo = "https://github.com/bazelbuild/rules_closure.git"
                git.Git(os.path.abspath(interpreter_curdir[-1])).clone(bazel_closure_repo)

            load_bazel_file(self.converter, os.path.join(closure_src, "BUILD"))
        elif url.startswith("//"):
            # Local file, do nothing
            if name not in loaded_projects.keys():
                loaded_projects.update({name: None})
                bazel_dir, bazel_file = url.replace("//", "").split(":")
                load_bazel_file(self.converter, os.path.abspath(os.path.join(interpreter_curdir[-1], bazel_dir, bazel_file)))
        else:
            print(args, kwargs)
            assert False

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
            self.__add_deps(kwargs)
        else:
            # Header-only library, have to do a couple things differently.
            # For some info, see:
            #  http://mariobadr.com/creating-a-header-only-library-with-cmake.html
            self.converter.toplevel += "add_library(%s INTERFACE)\n" % (
              kwargs["name"]
            )
            self.__add_deps(kwargs, " INTERFACE")

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
                load_bazel_file(self.converter, os.path.abspath(os.path.join(interpreter_curdir[-1], f)))
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
            load_bazel_file(self.converter, os.path.abspath(os.path.join(interpreter_curdir[-1], d_dir, d_file)))
        b_dir, b_file = srcs.replace("//", "").split(":")
        load_bazel_file(self.converter, os.path.abspath(os.path.join(interpreter_curdir[-1], b_dir, bfile)))
        assert False

    def genrule(self, **kwargs):
        assert False, "Failed to genrule"

    def config_setting(self, **kwargs):
        name = kwargs.get("name")
        values = kwargs.get("values")
        visibility = kwargs.get("visibility")

    def select(self, *args, **kwargs):
        print(args, kwargs)
        # TODO: store selections (this will become if statements)
        return []

    def glob(self, *args, **kwargs):
        patterns = args[0]
        total_files = []
        for pat in patterns:
            total_files.extend(glob.glob( os.path.abspath(os.path.join(interpreter_curdir[-1], pat)) ))
        exclude = kwargs.get("exclude", [])
        return list(filter(lambda f: f not in exclude, total_files))

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

    def provider(self, *args, **kwargs):
        print(args, kwargs)
        # info = args[0]
        #src = kwargs.get("fields").get("srcs")
        #transitive = kwargs.get("fields").get("transitive_srcs")

        #file_ext = kwargs.get("fields").get("file_ext")
        #failure_templ = kwargs.get("fields").get("failure_templ")

    def aspect(self, *args, **kwargs):
        pass

    def rule(self, *args, **kwargs):
        implementation = kwargs.get("implementation")
        attrs = kwargs.get("attrs")
        attrs_srcs = attrs.get("srcs")
        attrs_deps = attrs.get("deps")

    def label_list(self, *args, **kwargs):
        print(args, kwargs)
        assert False

    def repository_rule(self, *args, **kwargs):
        print(args, kwargs)
        """
        () {'implementation': <function _http_archive_impl at 0x106d16b00>,
            'attrs': {'url': None, 'urls': None, 'sha256': None, 'netrc': None, 'auth_patterns': None, 'canonical_id': None, 'strip_prefix': None, 'type': None, 'patches': None, 'patch_tool': None, 'patch_args': None, 'patch_cmds': None, 'patch_cmds_win': None, 'build_file': None, 'build_file_content': None, 'workspace_file': None, 'workspace_file_content': None},
                'doc': 'Downloads a Bazel repository as a compressed archive file, decompresses it,\nand makes its targets available for binding.\n\nIt supports the following file extensions: `"zip"`, `"jar"`, `"war"`, `"tar"`,\n`"tar.gz"`, `"tgz"`, `"tar.xz"`, and `tar.bz2`.\n\nExamples:\n  Suppose the current repository contains the source code for a chat program,\n  rooted at the directory `~/chat-app`. It needs to depend on an SSL library\n  which is available from http://example.com/openssl.zip. This `.zip` file\n  contains the following directory structure:\n\n  ```\n  WORKSPACE\n  src/\n    openssl.cc\n    openssl.h\n  ```\n\n  In the local repository, the user creates a `openssl.BUILD` file which\n  contains the following target definition:\n\n  ```python\n  cc_library(\n      name = "openssl-lib",\n      srcs = ["src/openssl.cc"],\n      hdrs = ["src/openssl.h"],\n  )\n  ```\n\n  Targets in the `~/chat-app` repository can depend on this target if the\n  following lines are added to `~/chat-app/WORKSPACE`:\n\n  ```python\n  load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")\n\n  http_archive(\n      name = "my_ssl",\n      urls = ["http://example.com/openssl.zip"],\n      sha256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",\n      build_file = "@//:openssl.BUILD",\n  )\n  ```\n\n  Then targets would specify `@my_ssl//:openssl-lib` as a dependency.\n'}
                """

class WorkspaceFileFunctions(BuildFileFunctions):
    def __init__(self, converter):
        super().__init__(converter)

    def workspace(self, **kwargs):
        name = kwargs.get("name")
        self.converter.prelude += "project(%s)\n" % (name)

    def local_repository(self, **kwargs):
        name = kwargs.get("name")
        path = kwargs.get("path")
        print("Loading subproject: " + name)
        if name not in loaded_projects.keys():
            loaded_projects.update({name: None})
            repo_dir = os.path.abspath(os.path.join(interpreter_curdir[-1], path))
            interpreter_curdir.append(repo_dir)
            subproject = load_subproject(proj_dir = repo_dir)
            loaded_projects.update({name: subproject})
            self.converter.add_subproject(subproject)
            interpreter_curdir.pop()

    def http_archive(self, **kwargs):
        name = kwargs.get("name")
        urls = kwargs.get("urls")
        url = kwargs.get("url")
        # handle the case when there is only one URL, make a list of 1
        if urls is None:
            urls = [url]

        strip_prefix = kwargs.get("strip_prefix")
        if name not in loaded_projects.keys():
            print("Fetching: " + name)
            dest_dir = os.path.abspath(os.path.join(interpreter_curdir[-1], name))
            extracted_dir = os.path.abspath(os.path.join(dest_dir, strip_prefix))
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
                        elif filename.endswith(".zip"):
                            with zipfile.ZipFile(os.path.join(dest_dir, filename), 'r') as zip_ref:
                                zip_ref.extractall(dest_dir)
                            break
                        else:
                            assert False, "Unknown file archive format"
                    except:
                        print("Failed to get repository")

            if os.path.exists(os.path.join(extracted_dir, "WORKSPACE")):
                loaded_projects.update({name: None})
                interpreter_curdir.append(extracted_dir)
                subproject = load_subproject(proj_dir = extracted_dir)
                loaded_projects.update({name: subproject})
                self.converter.add_subproject(subproject)
                interpreter_curdir.pop()
            elif os.path.exists(os.path.join(extracted_dir, "BUILD")):
                loaded_projects.update({name: None})
                load_bazel_file(self.converter, os.path.join(extracted_dir, "BUILD"))
                loaded_projects.update({name: None})
            elif os.path.exists(os.path.join(extracted_dir, "CMakeLists.txt")):
                loaded_projects.update({name: None})
                print("Found CMake Project!")
            else:
                print(kwargs)
                assert False, "Failed to get repository"

    def git_repository(self, **kwargs):
        assert False, "Failed to get git repository"

converter = Converter(os.curdir)

my_globs = {}

def load_bazel_file(converter, filename):
    with open(filename, "r") as f:
        print("Reading file" + filename)
        exec(f.read(), my_globs, GetDict(BuildFileFunctions(converter)))

def load_subproject(proj_dir):
    new_conv = Converter(proj_dir)
    with open(os.path.join(proj_dir, "WORKSPACE"), "r") as f:
        exec(f.read(), my_globs, GetDict(WorkspaceFileFunctions(converter)))
    if os.path.exists(os.path.join(proj_dir, "BUILD")):
        load_bazel_file(new_conv, os.path.join(proj_dir, "BUILD"))
    elif os.path.exists(os.path.join(proj_dir, "BUILD.bazel")):
        load_bazel_file(new_conv, os.path.join(proj_dir, "BUILD.bazel"))
    return new_conv

load_subproject(os.curdir)
#with open("WORKSPACE", "r") as workspace:
#    exec(workspace.read(), GetDict(WorkspaceFileFunctions(converter)))
#with open("BUILD", "r") as workspace:
#    exec(build.read(), GetDict(BuildFileFunctions(converter)))

with open(sys.argv[1], "w") as f:
  f.write(converter.convert())

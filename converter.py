import textwrap

class Converter(object):
    def __init__(self, proj_dir):
        self.prelude = ""
        self.toplevel = ""
        self.if_lua = ""
        self._subprojects = []
        self._proj_dir = proj_dir

    def add_subproject(self, new_proj):
        self._subprojects.append(new_proj)

    def convert(self):
        return self.template % {
            "prelude": converter.prelude,
            "toplevel": converter.toplevel,
        }

    template = textwrap.dedent("""\
        # This file was generated from BUILD using tools/make_cmakelists.py.

        cmake_minimum_required(VERSION 3.1)

        if(${CMAKE_VERSION} VERSION_LESS 3.12)
            cmake_policy(VERSION ${CMAKE_MAJOR_VERSION}.${CMAKE_MINOR_VERSION})
        else()
            cmake_policy(VERSION 3.12)
        endif()

        cmake_minimum_required (VERSION 3.0)
        cmake_policy(SET CMP0048 NEW)

        %(prelude)s

        # Prevent CMake from setting -rdynamic on Linux (!!).
        SET(CMAKE_SHARED_LIBRARY_LINK_C_FLAGS "")
        SET(CMAKE_SHARED_LIBRARY_LINK_CXX_FLAGS "")

        # Set default build type.
        if(NOT CMAKE_BUILD_TYPE)
          message(STATUS "Setting build type to 'RelWithDebInfo' as none was specified.")
          set(CMAKE_BUILD_TYPE "RelWithDebInfo" CACHE STRING
              "Choose the type of build, options are: Debug Release RelWithDebInfo MinSizeRel."
              FORCE)
        endif()

        # When using Ninja, compiler output won't be colorized without this.
        include(CheckCXXCompilerFlag)
        CHECK_CXX_COMPILER_FLAG(-fdiagnostics-color=always SUPPORTS_COLOR_ALWAYS)
        if(SUPPORTS_COLOR_ALWAYS)
          set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fdiagnostics-color=always")
        endif()

        # Implement ASAN/UBSAN options
        if(UPB_ENABLE_ASAN)
          set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fsanitize=address")
          set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -fsanitize=address")
          set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -fsanitize=address")
          set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} -fsanitize=address")
        endif()

        if(UPB_ENABLE_UBSAN)
          set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fsanitize=undefined")
          set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -fsanitize=address")
          set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -fsanitize=address")
          set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} -fsanitize=address")
        endif()

        include_directories(.)
        include_directories(${CMAKE_CURRENT_BINARY_DIR})

        if(APPLE)
          set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} -undefined dynamic_lookup -flat_namespace")
        elseif(UNIX)
          set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -Wl,--build-id")
        endif()

        enable_testing()

        %(toplevel)s

        """)

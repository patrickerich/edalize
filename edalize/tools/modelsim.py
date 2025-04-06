# Copyright edalize contributors
# Licensed under the 2-Clause BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-2-Clause

from io import StringIO
import os
import logging

from edalize.tools.edatool import Edatool
from edalize.utils import EdaCommands

logger = logging.getLogger(__name__)

class Modelsim(Edatool):

    description = "ModelSim/Questa simulator from Mentor Graphics/Siemens EDA"

    TOOL_OPTIONS = {
        "compilation_mode": {
            "type": "str",
            "desc": "Common or separate compilation, sep - for separate compilation, common - for common compilation",
        },
        "vcom_options": {
            "type": "str",
            "desc": "Additional options for compilation with vcom",
        },
        "vlog_options": {
            "type": "str",
            "desc": "Additional options for compilation with vlog",
        },
        "vsim_options": {
            "type": "str",
            "desc": "Additional run options for vsim",
        },
    }

    def setup(self, edam):
        super().setup(edam)

        # Create TCL script for building RTL
        self.tcl_build_rtl = StringIO()
        self.tcl_build_rtl.write("onerror { quit -code 1; }\n")

        # Create main TCL script
        self.tcl_main = StringIO()
        self.tcl_main.write("onerror { quit -code 1; }\n")
        self.tcl_main.write("do edalize_build_rtl.tcl\n")

        # Get source files and include directories
        src_files = []
        incdirs = []
        vlog_include_dirs = []
        libs = []
        vlog_files = []

        for f in self.files:
            if not f.get("logical_name"):
                f["logical_name"] = "work"
            if not f["logical_name"] in libs:
                self.tcl_build_rtl.write("vlib {}\n".format(f["logical_name"]))
                libs.append(f["logical_name"])
            
            if self._add_include_dir(f, incdirs):
                continue
                
            file_type = f.get("file_type", "")
            if file_type.startswith("verilogSource") or file_type.startswith("systemVerilogSource"):
                vlog_files.append(f)
                cmd = "vlog"
                args = []

                args += self.tool_options.get("vlog_options", [])

                for k, v in self.vlogdefine.items():
                    args += ["+define+{}={}".format(k, self._param_value_str(v))]

                if file_type.startswith("systemVerilogSource"):
                    args += ["-sv"]
                
                if not self.tool_options.get("compilation_mode") == "common":
                    args += ["-quiet"]
                    args += ["-work", f["logical_name"]]
                    args += [f["name"].replace("\\", "/")]
                    self.tcl_build_rtl.write("{} {}\n".format(cmd, " ".join(args)))
            
            elif file_type.startswith("vhdlSource"):
                cmd = "vcom"
                if file_type.endswith("-87"):
                    args = ["-87"]
                elif file_type.endswith("-93"):
                    args = ["-93"]
                elif file_type.endswith("-2008"):
                    args = ["-2008"]
                else:
                    args = []

                args += self.tool_options.get("vcom_options", [])
                args += ["-quiet"]
                args += ["-work", f["logical_name"]]
                args += [f["name"].replace("\\", "/")]
                self.tcl_build_rtl.write("{} {}\n".format(cmd, " ".join(args)))
            
            elif file_type == "tclSource":
                self.tcl_main.write("do {}\n".format(f["name"]))
            
            elif file_type == "user":
                pass
            else:
                _s = "{} has unknown file type '{}'"
                logger.warning(_s.format(f["name"], file_type))

        # Handle common compilation mode for Verilog files
        if self.tool_options.get("compilation_mode") == "common" and vlog_files:
            args = self.tool_options.get("vlog_options", [])
            for k, v in self.vlogdefine.items():
                args += ["+define+{}={}".format(k, self._param_value_str(v))]

            _vlog_files = []
            has_sv = False
            for f in vlog_files:
                _vlog_files.append(f["name"].replace("\\", "/"))
                if f.get("file_type", "").startswith("systemVerilogSource"):
                    has_sv = True

            if has_sv:
                args += ["-sv"]
            
            for incdir in incdirs:
                args += ["+incdir+" + incdir.replace("\\", "/")]
                
            args += ["-quiet"]
            args += ["-work", "work"]
            args += ["-mfcu"]
            self.tcl_build_rtl.write("vlog {} {}\n".format(" ".join(args), " ".join(_vlog_files)))

        # Create shell script for building
        self.build_sh = StringIO()
        self.build_sh.write("#!/bin/bash\n")
        self.build_sh.write("set -e\n")
        self.build_sh.write("vsim -c -do 'source edalize_main.tcl; exit'\n")

        # Create shell script for running
        self.run_sh = StringIO()
        self.run_sh.write("#!/bin/bash\n")
        self.run_sh.write("set -e\n")
        
        # Prepare parameters and plusargs
        _parameters = []
        for key, value in self.vlogparam.items():
            _parameters.append("-g{}={}".format(key, self._param_value_str(value)))
        for key, value in self.generic.items():
            _parameters.append("-g{}={}".format(key, self._param_value_str(value, bool_is_str=True)))
        
        _plusargs = []
        for key, value in self.plusarg.items():
            _plusargs.append("+{}={}".format(key, self._param_value_str(value)))
        
        _vsim_options = self.tool_options.get("vsim_options", [])
        
        # Add VPI modules support if needed
        _vpi_options = []
        for vpi_module in self.vpi_modules:
            _vpi_options.append("-pli {}".format(vpi_module["name"]))
        
        # Build the run command
        run_cmd = "vsim -c {} {} {} {} -do 'run -all; quit -code 0; exit' {}".format(
            " ".join(_vpi_options),
            " ".join(_vsim_options),
            " ".join(_parameters),
            " ".join(_plusargs),
            self.toplevel
        )
        self.run_sh.write(run_cmd + "\n")
        
        # Create commands
        commands = EdaCommands()
        commands.add(["bash", "build.sh"], ["build"], [])
        commands.set_default_target("build")
        self.commands = commands

    def write_config_files(self):
        self.update_config_file("edalize_build_rtl.tcl", self.tcl_build_rtl.getvalue())
        self.update_config_file("edalize_main.tcl", self.tcl_main.getvalue())
        self.update_config_file("build.sh", self.build_sh.getvalue())
        self.update_config_file("run.sh", self.run_sh.getvalue())
        
        # Make shell scripts executable
        os.chmod(os.path.join(self.work_root, "build.sh"), 0o755)
        os.chmod(os.path.join(self.work_root, "run.sh"), 0o755)

    def run(self):
        return ("bash", ["run.sh"], self.work_root)


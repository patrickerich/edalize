# Copyright edalize contributors
# Licensed under the 2-Clause BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-2-Clause

from io import StringIO
import os
import logging

from edalize.tools.edatool import Edatool
from edalize.utils import EdaCommands

logger = logging.getLogger(__name__)

class Xcelium(Edatool):

    description = "Xcelium simulator from Cadence"

    TOOL_OPTIONS = {
        "xmvhdl_options": {
            "type": "str",
            "desc": "Additional options for xmvhdl",
        },
        "xmvlog_options": {
            "type": "str",
            "desc": "Additional options for xmvlog",
        },
        "xmsim_options": {
            "type": "str",
            "desc": "Additional options for xmsim",
        },
        "xrun_options": {
            "type": "str",
            "desc": "Additional options for xrun",
        },
        "xelab_options": {
            "type": "str",
            "desc": "Additional options for xelab",
        },
    }

    def setup(self, edam):
        super().setup(edam)

        # Create build script
        self.build_sh = StringIO()
        self.build_sh.write("#!/bin/bash\n")
        self.build_sh.write("set -e\n")
        
        # Create run script
        self.run_sh = StringIO()
        self.run_sh.write("#!/bin/bash\n")
        self.run_sh.write("set -e\n")
        
        # Prepare file lists
        src_files = []
        incdirs = []
        src_files_filtered = []
        vlog_files = []
        vhdl_files = []
        
        for f in self.files:
            if self._add_include_dir(f, incdirs):
                continue
                
            file_type = f.get("file_type", "")
            
            if file_type.startswith("verilogSource") or file_type.startswith("systemVerilogSource"):
                vlog_files.append(f)
                src_files_filtered.append(f)
            elif file_type.startswith("vhdlSource"):
                vhdl_files.append(f)
                src_files_filtered.append(f)
            elif file_type == "user":
                pass
            else:
                _s = "{} has unknown file type '{}'"
                logger.warning(_s.format(f["name"], file_type))
        
        # Prepare compilation commands
        xrun_options = self.tool_options.get("xrun_options", [])
        xmvlog_options = self.tool_options.get("xmvlog_options", [])
        xmvhdl_options = self.tool_options.get("xmvhdl_options", [])
        xmsim_options = self.tool_options.get("xmsim_options", [])
        
        # Define compilation command
        compile_cmd = "xrun"
        compile_cmd += " -elaborate" # Just compile, don't run simulation
        compile_cmd += " -xmlibdirname ./xcelium.d"
        compile_cmd += " -log xrun.log"
        
        # Add include directories
        for incdir in incdirs:
            compile_cmd += f" -incdir {incdir}"
        
        # Add verilog defines
        for k, v in self.vlogdefine.items():
            compile_cmd += f" -define {k}={self._param_value_str(v)}"
        
        # Add tool options
        if xrun_options:
            compile_cmd += " " + " ".join(xrun_options)
        if xmvlog_options:
            compile_cmd += " -xmvlog_opts \"" + " ".join(xmvlog_options) + "\""
        if xmvhdl_options:
            compile_cmd += " -xmvhdl_opts \"" + " ".join(xmvhdl_options) + "\""
        
        # Add source files
        for f in vlog_files:
            if f.get("file_type", "").startswith("systemVerilogSource"):
                compile_cmd += f" -sv {f['name']}"
            else:
                compile_cmd += f" -v {f['name']}"
        
        for f in vhdl_files:
            compile_cmd += f" -vhdl {f['name']}"
        
        # Add top level
        compile_cmd += f" -top {self.toplevel}"
        
        # Write compile command to build script
        self.build_sh.write(compile_cmd + "\n")
        
        # Define run command
        run_cmd = "xrun"
        run_cmd += " -R" # Run simulation
        run_cmd += " -xmlibdirname ./xcelium.d"
        run_cmd += " -log xrun_sim.log"
        
        # Add parameters
        for key, value in self.vlogparam.items():
            param_value = self._param_value_str(value)
            run_cmd += f" -defparam {self.toplevel}.{key}={param_value}"
        
        # Add plusargs
        for key, value in self.plusarg.items():
            run_cmd += f" +{key}={self._param_value_str(value)}"
        
        # Add simulation options
        if xmsim_options:
            run_cmd += " -xmsimargs \"" + " ".join(xmsim_options) + "\""
        
        # Write run command to run script
        self.run_sh.write(run_cmd + "\n")
        
        # Create commands
        commands = EdaCommands()
        commands.add(["bash", "build.sh"], ["build"], [])
        commands.set_default_target("build")
        self.commands = commands

    def write_config_files(self):
        self.update_config_file("build.sh", self.build_sh.getvalue())
        self.update_config_file("run.sh", self.run_sh.getvalue())
        
        # Make shell scripts executable
        os.chmod(os.path.join(self.work_root, "build.sh"), 0o755)
        os.chmod(os.path.join(self.work_root, "run.sh"), 0o755)

    def run(self):
        return ("bash", ["run.sh"], self.work_root)


#Auto generated by Edalize

all: design.simv

design.simv: vlog_incfile sv_file.sv vlog_file.v vlog_with_define.v vlog05_file.v another_sv_file.sv vcs.f parameters.txt
	$(EDALIZE_LAUNCHER) vcs -full64 -o design.simv -file vcs.f -parameters parameters.txt sv_file.sv vlog_file.v vlog_with_define.v vlog05_file.v another_sv_file.sv

run:
	$(EDALIZE_LAUNCHER) ./design.simv $(EXTRA_OPTIONS)

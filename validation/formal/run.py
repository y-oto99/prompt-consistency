"""Execute the SMT-LIB checks with an installed Z3 binary or shared library."""

import ctypes
import ctypes.util
from pathlib import Path
import shutil
import subprocess


def replay():
    source = Path(__file__).with_name("approval.smt2")
    binary = shutil.which("z3")
    if binary:
        result = subprocess.run(
            [binary, "-smt2", source], check=True, text=True, capture_output=True
        ).stdout
    else:
        lib = ctypes.util.find_library("z3")
        if not lib:
            raise RuntimeError("Z3 executable or shared library required for SMT replay")
        z3 = ctypes.CDLL(lib)
        z3.Z3_mk_config.restype = ctypes.c_void_p
        z3.Z3_del_config.argtypes = [ctypes.c_void_p]
        z3.Z3_mk_context.argtypes = [ctypes.c_void_p]
        z3.Z3_mk_context.restype = ctypes.c_void_p
        z3.Z3_del_context.argtypes = [ctypes.c_void_p]
        z3.Z3_eval_smtlib2_string.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        z3.Z3_eval_smtlib2_string.restype = ctypes.c_char_p
        config = z3.Z3_mk_config()
        context = z3.Z3_mk_context(config)
        z3.Z3_del_config(config)
        try:
            result = z3.Z3_eval_smtlib2_string(context, source.read_bytes()).decode("utf-8")
        finally:
            z3.Z3_del_context(context)
    verdicts = [line.strip() for line in result.splitlines() if line.strip() in {"sat", "unsat", "unknown"}]
    if verdicts != ["unsat", "unsat", "sat"]:
        raise RuntimeError(f"unexpected SMT replay:\n{result}")
    return result


if __name__ == "__main__":
    print(replay(), end="")

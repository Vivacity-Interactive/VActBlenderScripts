_vactsetup = {
    "ready": False,
    "verbose": True,
    "exceptions": [],
    "trace": [],
    "deps" : [
        "pip",
        "numpy"
    ],
    "assert_deps" : [
        "numpy"
    ],
    "pkg_dir": "python_lib",
    "python_lib": None
}

class _VActImport:
    @classmethod
    def module(cls, name):
        import importlib
        _module = importlib.import_module(name)
        if not _module: raise ModuleNotFoundError()
        return _module

def _execute():
    np = _VActImport.module("numpy")
    _arr = np.identity(3)
    print(_arr)

def _vact_setup():
    _vactsetup["ready"] = False
    try:
        for dep in _vactsetup["assert_deps"]:
            _VActImport.module(dep)

        _vactsetup["ready"] = True
    except Exception as ex0:
        _vactsetup["exceptions"] += [ex0]
        import sys
        import os
        import subprocess
        
        # Find python executable
        python_exe = os.path.join(sys.prefix, 'bin', 'python.exe')#sys.executable
        
        # Ensure user library path
        pkg_dir = _vactsetup["python_lib"]
        if (not pkg_dir) and _vactsetup["pkg_dir"]:
            plugin_dir = os.path.dirname(bpy.data.filepath) or os.getcwd()
            pkg_dir = _vactsetup["python_lib"] = os.path.join(plugin_dir, _vactsetup["pkg_dir"])
            os.makedirs(pkg_dir, exist_ok=True)
            if pkg_dir and pkg_dir not in sys.path: sys.path.insert(0, pkg_dir)
        
        _vactsetup["trace"] += [subprocess.run([python_exe, "-m", "ensurepip"])]
        for dep in _vactsetup["deps"]:
            if _vactsetup["verbose"]: print("_vact_setup: install pip '" + dep + "'")
            if pkg_dir: _vactsetup["trace"] += [subprocess.run([python_exe, "-m", "pip", "install", "--upgrade", "--target", pkg_dir, dep])]
            else: _vactsetup["trace"] += [subprocess.run([python_exe, "-m", "pip", "install", "--upgrade", dep])]
        
        try:
            # Check for incomplete dependencies
            for complete in _vactsetup["trace"]:
                complete.check_returncode()

            for dep in _vactsetup["assert_deps"]:
                _VActImport.module(dep)
            
            _vactsetup["ready"] = True
        except Exception as ex1:
            _vactsetup["exceptions"] += [ex1]
    
    return _vactsetup["ready"]

if __name__ == "__main__":
    if not _vact_setup():
        print(_vactsetup["exceptions"])
        raise Exception("Dependencies could't be loaded, try install dependencies manually to Blender-Python")
    print("_vact_setup: success")
    _execute()
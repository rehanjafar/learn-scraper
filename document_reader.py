"""Run the parser with CPU, memory, time and macOS filesystem/network restrictions."""
import json,os,subprocess,sys
from pathlib import Path
from fastmcp.exceptions import ToolError
ROOT=Path(__file__).resolve().parent

def sandbox_profile():
    worker=ROOT/'document_worker.py';venv=Path(sys.prefix).resolve();executable=Path(sys.executable).resolve()
    framework=(Path(sys.base_prefix)/'Resources/Python.app/Contents/MacOS/Python').resolve()
    quote=lambda p:json.dumps(str(p))
    readpaths=['/System','/usr/lib','/usr/share','/opt/homebrew','/Library/Apple',str(venv)]
    literals=[str(worker),'/dev/null','/dev/urandom','/private/etc/localtime']
    return ('(version 1)(deny default)(allow sysctl-read)(allow file-read-metadata)'
            +'(allow process-exec (literal '+quote(executable)+')(literal '+quote(framework)+'))'
            +'(allow file-read-data '+''.join('(subpath '+quote(p)+')' for p in readpaths)
            +''.join('(literal '+quote(p)+')' for p in literals)+')'
            +'(import "dyld-support.sb")(allow file-map-executable (subpath "/opt/homebrew") (subpath '+quote(venv)+'))')

def read_document(file,start_unit=1,max_units=12):
    if sys.platform!='darwin' or not Path('/usr/bin/sandbox-exec').exists():
        raise ToolError('The protected document reader currently requires the macOS parser sandbox.')
    payload={k:file[k] for k in ('base64','size','sha256','format')}
    payload.update(start_unit=start_unit,max_units=max_units)
    if len(payload['base64'])>5600000:raise ToolError('Document exceeds the protected reader limit.')
    command=['/usr/bin/sandbox-exec','-p',sandbox_profile(),sys.executable,'-I','-B',str(ROOT/'document_worker.py')]
    try:
        from resource_guard import run_guarded
        code,stdout,_=run_guarded(command,json.dumps(payload).encode(),
            {'PATH':'/usr/bin:/bin','LANG':'en_US.UTF-8','PYTHONDONTWRITEBYTECODE':'1','DOCUMENT_MEMORY_GUARD':'parent-rss-v1'})
        if code or len(stdout)>1500000:raise ValueError()
        parsed=json.loads(stdout)
        if 'error' in parsed:raise ToolError(parsed['error'])
        return parsed
    except (ValueError,KeyError,RuntimeError,subprocess.TimeoutExpired):
        raise ToolError('The protected document parser could not complete safely. No file was opened as an application.')

"""Linux document parser: isolated filesystem/network, hard resource limits, bounded pipes."""
import concurrent.futures,json,os,signal,subprocess,time
from pathlib import Path
from fastmcp.exceptions import ToolError
ROOT=Path(__file__).resolve().parent

def sandbox_command(worker=None):
    worker=Path(worker or ROOT/'document_worker.py').resolve()
    command=['/usr/bin/bwrap','--unshare-all','--die-with-parent','--cap-drop','ALL','--clearenv',
             '--setenv','LANG','C.UTF-8','--setenv','PATH','/usr/bin',
             '--ro-bind','/usr','/usr','--ro-bind','/lib','/lib']
    if Path('/lib64').exists():command+=['--ro-bind','/lib64','/lib64']
    command+=['--proc','/proc','--dev','/dev','--tmpfs','/tmp','--dir','/runtime',
              '--ro-bind',str(ROOT/'.venv'),'/runtime/venv',
              '--ro-bind',str(worker),'/runtime/document_worker.py',
              '--chdir','/tmp','--','/runtime/venv/bin/python','-I','-B','/runtime/document_worker.py']
    return command

def run_isolated(command,payload,timeout=9):
    if len(payload)>6000000:raise ValueError('Input bound exceeded')
    # Popen from the MCP tool thread must not run Python preexec callbacks.
    # prlimit applies hard limits before bwrap or the parser starts.
    command=['/usr/bin/prlimit','--as=805306368:805306368','--cpu=5:5','--fsize=0:0','--nofile=64:64','--']+command
    process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                             env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'},start_new_session=True)
    def kill():
        try:os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:pass
    def write():
        try:process.stdin.write(payload);process.stdin.close()
        except (BrokenPipeError,OSError):pass
    started=time.monotonic()
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            writer=pool.submit(write);reader=pool.submit(process.stdout.read,1500001)
            try:
                while not reader.done() or process.poll() is None:
                    if reader.done() and len(reader.result())>1500000:raise RuntimeError('Output bound exceeded')
                    if time.monotonic()-started>timeout:raise RuntimeError('Elapsed-time bound exceeded')
                    time.sleep(.01)
                output=reader.result();writer.result()
                if len(output)>1500000:raise RuntimeError('Output bound exceeded')
                return process.returncode,output
            finally:kill()
    finally:
        kill();process.wait(timeout=2)
        process.stdout.close()
        if not process.stdin.closed:process.stdin.close()

def read_document_linux(file,start_unit=1,max_units=12):
    if not all(Path(p).is_file() for p in ('/usr/bin/bwrap','/usr/bin/prlimit')):
        raise ToolError('Protected Linux document isolation is unavailable.')
    try:
        payload={k:file[k] for k in ('base64','size','sha256','format')}
        payload.update(start_unit=start_unit,max_units=max_units)
        if len(payload['base64'])>5600000:raise ValueError()
        code,output=run_isolated(sandbox_command(),json.dumps(payload).encode())
        if code:raise ValueError()
        result=json.loads(output)
        if 'error' in result:raise ValueError()
        return result
    except (ValueError,KeyError,RuntimeError,OSError,subprocess.SubprocessError):
        raise ToolError('Protected document extraction could not complete safely.')

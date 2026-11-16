"""macOS child-process RSS and elapsed-time guard. Fails closed if monitoring fails."""
import concurrent.futures,ctypes,json,subprocess,time

def run_guarded(command,payload,env,max_resident=384*1024*1024,timeout=9):
    lib=ctypes.CDLL('/usr/lib/libproc.dylib',use_errno=True)
    lib.proc_pidinfo.argtypes=[ctypes.c_int,ctypes.c_int,ctypes.c_uint64,ctypes.c_void_p,ctypes.c_int]
    lib.proc_pidinfo.restype=ctypes.c_int
    process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env=env)
    started=time.monotonic()
    def write_input():
        try:process.stdin.write(payload);process.stdin.close()
        except (BrokenPipeError,OSError):pass
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            writer=pool.submit(write_input)
            reader=pool.submit(process.stdout.read,1500001)
            while not reader.done() or process.poll() is None:
                if reader.done() and len(reader.result())>1500000:
                    process.kill();raise RuntimeError('Child output bound exceeded.')
                if process.poll() is None:
                    info=ctypes.create_string_buffer(96)
                    amount=lib.proc_pidinfo(process.pid,4,0,info,96)
                    if amount>=16:
                        resident=ctypes.c_uint64.from_buffer_copy(info.raw[8:16]).value
                        if resident>max_resident:
                            process.kill();raise RuntimeError('Child process exceeded the resident-memory bound.')
                    elif time.monotonic()-started>.25 and process.poll() is None:
                        process.kill();raise RuntimeError('Child memory monitoring is unavailable.')
                if time.monotonic()-started>timeout:
                    process.kill();raise RuntimeError('Child process exceeded the elapsed-time bound.')
                time.sleep(.02)
            stdout=reader.result();writer.result()
        if len(stdout)>1500000:raise RuntimeError('Child output bound exceeded.')
        return process.returncode,stdout,b''
    finally:
        if process.poll() is None:process.kill()
        process.wait(timeout=2)
        process.stdout.close()

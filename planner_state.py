"""Private, bounded, atomic local tracker; no account credentials or document binaries."""
import argparse,fcntl,json,os,re,stat,tempfile
from contextlib import contextmanager
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent
CATEGORIES={'course_progress','deadlines','projects','applications','startups','articles','calendar_events','source_scans'}
DEFAULT_PROFILE={'timezone':'America/Toronto','courses':['CS135','MATH135','MATH137','COMMST223','SCI238'],'career_season':'Summer 2027','career_targets':['SWE internship','systems','infrastructure','ML engineering'],'career_locations':['Canada','compatible remote'],'calendar_name':'Daily Plan','wake_mode':'manual Morning run or user-configured Shortcut','wake_automation_configured':False,'resume_path':None,'linkedin_url':None,'x_handle':'rehanjfr'}
@contextmanager
def locked():
    directory=ROOT/'planner_state'
    directory.mkdir(mode=0o700,exist_ok=True)
    info=directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077:raise RuntimeError('Planner storage must be private and owned by this user.')
    fd=os.open(directory/'state.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX);yield directory
    finally:os.close(fd)
def load(directory):
    path=directory/'state.json'
    if not path.exists():return {'schema':1,'profile':DEFAULT_PROFILE.copy(),'records':{category:{} for category in sorted(CATEGORIES)}}
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077 or info.st_size>2000000:raise RuntimeError('Invalid private planner state file.')
        with os.fdopen(fd,'r',closefd=False) as handle:return json.load(handle)
    finally:os.close(fd)
def get_state():
    with locked() as directory:return load(directory)
def record(category,key,value,source='explicit_user'):
    if category not in CATEGORIES or not isinstance(key,str) or not 0<len(key)<=250 or not isinstance(value,dict):raise ValueError('Invalid planner record.')
    if len(json.dumps(value))>32000:raise ValueError('Planner record is too large.')
    if category=='course_progress' and any(value.get(k) is True for k in ('seen','independent','submitted')) and source not in ('explicit_user','verified_learn'):
        raise ValueError('Progress cannot be inferred merely from reading materials.')
    if category=='startups':
        from urllib.parse import urlsplit
        candidate=key if '://' in key else 'https://'+key
        parsed=urlsplit(candidate);key=(parsed.hostname or '').lower().removeprefix('www.')
        if not key or parsed.username or parsed.password:raise ValueError('Invalid canonical startup domain.')
    with locked() as directory:
        state=load(directory);state['records'][category][key]={'value':value,'source':source,'updated_at':datetime.now(timezone.utc).isoformat()}
        raw=json.dumps(state,ensure_ascii=False).encode()
        if len(raw)>2000000:raise ValueError('Planner state has reached its storage bound.')
        fd,name=tempfile.mkstemp(dir=directory,prefix='state-',suffix='.tmp')
        try:
            with os.fdopen(fd,'wb') as handle:handle.write(raw);handle.flush();os.fsync(handle.fileno())
            os.replace(name,directory/'state.json')
        finally:
            if os.path.exists(name):os.unlink(name)
        return {'saved':True,'category':category,'key':key}
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--record',action='store_true');args=parser.parse_args()
    if args.record:
        import sys
        data=json.loads(sys.stdin.read(40000));print(json.dumps(record(**data)))
    else:print(json.dumps(get_state(),ensure_ascii=False))

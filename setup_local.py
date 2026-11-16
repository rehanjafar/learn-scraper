"""Create a per-install local pairing key; never put it in the app or Git."""
import argparse,os,secrets
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument('--show-pairing-key',action='store_true',help='Display the pairing key locally for entry in Safari; never share it.')
args=parser.parse_args()
root=Path(__file__).resolve().parent/'safari-reader'
root.mkdir(exist_ok=True)
key=root/'token'
if not key.exists():
 fd=os.open(key,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w') as out:out.write(secrets.token_urlsafe(32))
key.chmod(0o600)
print('Local setup ready. No browser session or password was accessed.')
if args.show_pairing_key:
 print('Enter this key only in the Waterloo Safari Reader popup on this Mac:')
 print(key.read_text())

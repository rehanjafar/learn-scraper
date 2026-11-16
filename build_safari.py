"""Build a sandboxed, development-signed Safari extension without weakening Safari."""
import argparse,os,plistlib,subprocess
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument('--distribution-check',action='store_true',help='Require Gatekeeper distribution acceptance; separate from local Xcode development testing.')
args=parser.parse_args()
root=Path(__file__).resolve().parent
work=root/'safari-reader';project=work/'project'
app='Waterloo Safari Reader';bundle='ca.rehan.waterloo-safari-reader'
team=os.environ['DEVELOPMENT_TEAM'];identity=os.environ['SIGNING_IDENTITY']
if not project.exists():
 subprocess.run(['xcrun','safari-web-extension-converter',str(work/'extension'),'--project-location',str(project),'--app-name',app,'--bundle-identifier',bundle,'--swift','--macos-only','--no-open','--no-prompt'],check=True)
proj=project/app/(app+'.xcodeproj')
p=proj/'project.xcproj'
if not p.exists():raise RuntimeError('This hardened builder requires the current Xcode project format; review older formats manually.')
s=p.read_text().replace('ca.rehan.Waterloo-Safari-Reader',bundle)
s=s.replace('"ENABLE_OUTGOING_NETWORK_CONNECTIONS": "YES"','"ENABLE_OUTGOING_NETWORK_CONNECTIONS": "NO"')
s=s.replace('"ENABLE_USER_SELECTED_FILES": "readonly"','"ENABLE_USER_SELECTED_FILES": "NO"')
for name,entitlements in [(app,{'com.apple.security.app-sandbox':True}),(app+' Extension',{'com.apple.security.app-sandbox':True,'com.apple.security.network.client':True})]:
 (project/app/name/'Reader.entitlements').write_bytes(plistlib.dumps(entitlements))
setting='"CODE_SIGN_ENTITLEMENTS":'
if setting not in s:
 needle='"CODE_SIGN_STYLE": "Automatic",';a=s.find(needle);b=s.find(needle,a+len(needle))
 if a<0 or b<0:raise RuntimeError('Unexpected Xcode signing settings; refusing to build.')
 s=s[:b]+s[b:].replace(needle,needle+'\n        "CODE_SIGN_ENTITLEMENTS": "Waterloo Safari Reader Extension/Reader.entitlements",',1)
 s=s[:a]+s[a:].replace(needle,needle+'\n        "CODE_SIGN_ENTITLEMENTS": "Waterloo Safari Reader/Reader.entitlements",',1)
p.write_text(s)
handler=project/app/(app+' Extension')/'SafariWebExtensionHandler.swift'
handler.write_text('import SafariServices\nclass SafariWebExtensionHandler: NSObject, NSExtensionRequestHandling {\n func beginRequest(with context: NSExtensionContext) { context.cancelRequest(withError: NSError(domain: "NativeMessagingDisabled", code: 1)) }\n}\n')
subprocess.run(['xcodebuild','-project',str(proj),'-scheme',app,'-configuration','Release','-derivedDataPath',str(work/'build'),'DEVELOPMENT_TEAM='+team,'CODE_SIGN_STYLE=Manual','CODE_SIGN_IDENTITY='+identity,'CODE_SIGN_INJECT_BASE_ENTITLEMENTS=NO','build'],check=True)
built=work/'build/Build/Products/Release'/(app+'.app')
subprocess.run(['codesign','--verify','--deep','--strict',str(built)],check=True)
subprocess.run(['codesign','--verify','-R','=anchor apple generic and certificate leaf[subject.OU] = "'+team+'"',str(built)],check=True)
for target,expected in [(built,{'com.apple.security.app-sandbox':True}),(built/'Contents/PlugIns'/(app+' Extension.appex'),{'com.apple.security.app-sandbox':True,'com.apple.security.network.client':True})]:
 result=subprocess.run(['codesign','-d','--entitlements',':-',str(target)],capture_output=True,check=True)
 raw=result.stdout+result.stderr;i=raw.find(b'<?xml');j=raw.find(b'</plist>',i)
 if i<0 or j<0 or plistlib.loads(raw[i:j+8])!=expected:raise RuntimeError('Unexpected signed entitlements; do not enable this build.')
print('Signature and minimum sandbox entitlements verified:',built)
print('No Safari or macOS security settings were changed. Enable manually in Safari only if its normal extension controls accept the signed build.')
if args.distribution_check:subprocess.run(['spctl','--assess','--type','execute',str(built)],check=True)

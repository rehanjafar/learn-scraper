"""Build the Safari extension using your local Apple Development identity."""
import os,subprocess
from pathlib import Path
root=Path(__file__).resolve().parent
work=root/'safari-reader'
project=work/'project'
app='Waterloo Safari Reader'
bundle='ca.rehan.waterloo-safari-reader'
team=os.environ['DEVELOPMENT_TEAM']
identity=os.environ['SIGNING_IDENTITY']
if not project.exists():
 subprocess.run(['xcrun','safari-web-extension-converter',str(work/'extension'),'--project-location',str(project),'--app-name',app,'--bundle-identifier',bundle,'--swift','--macos-only','--no-open','--no-prompt'],check=True)
proj=project/app/(app+'.xcodeproj')
for filename in ('project.xcproj','project.pbxproj'):
 p=proj/filename
 if p.exists():
  text=p.read_text().replace('ca.rehan.Waterloo-Safari-Reader',bundle)
  p.write_text(text)
handler=project/app/(app+' Extension')/'SafariWebExtensionHandler.swift'
handler.write_text('import SafariServices\nclass SafariWebExtensionHandler: NSObject, NSExtensionRequestHandling {\n func beginRequest(with context: NSExtensionContext) { context.cancelRequest(withError: NSError(domain: "NativeMessagingDisabled", code: 1)) }\n}\n')
subprocess.run(['xcodebuild','-project',str(proj),'-scheme',app,'-configuration','Release','-derivedDataPath',str(work/'build'),'DEVELOPMENT_TEAM='+team,'CODE_SIGN_STYLE=Manual','CODE_SIGN_IDENTITY='+identity,'ENABLE_OUTGOING_NETWORK_CONNECTIONS=YES','CODE_SIGN_INJECT_BASE_ENTITLEMENTS=NO','ENABLE_USER_SELECTED_FILES=NO','build'],check=True)
built=work/'build/Build/Products/Release'/(app+'.app')
subprocess.run(['codesign','--verify','--deep','--strict',str(built)],check=True)
print('Built and signature-verified:',built)
subprocess.run(['spctl','--assess','--type','execute',str(built)],check=True)
print('Gatekeeper accepted this build. Live Safari testing is still required.')

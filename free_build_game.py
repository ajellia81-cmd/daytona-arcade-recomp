"""Build with private inputs; all post-decryption compiler output stays encrypted."""
from pathlib import Path
import shutil
import subprocess
import sys

platform = sys.argv[1]
package = Path('private-package')
package.mkdir(exist_ok=True)
log = (package / 'private-build.log').open('w', encoding='utf-8')

def run(args, cwd=None):
    result = subprocess.run(args, cwd=cwd, stdout=log, stderr=subprocess.STDOUT)
    log.flush()
    if result.returncode:
        raise RuntimeError('Private build command failed; inspect encrypted build log')

try:
    roms = Path('source/roms'); roms.mkdir(exist_ok=True)
    shutil.copyfile('private-input/daytona.zip', roms / 'daytona.zip')
    p = Path('source/src/runtime/rom_import.cpp'); s = p.read_text()
    for old, new in {'mpr-16537.ic28':'mpr-16537.28','mpr-16536.ic29':'mpr-16536.29','mpr-16523.ic16':'mpr-16523.16','mpr-16518.ic20':'mpr-16518.20','mpr-16524.ic17':'mpr-16524.17','mpr-16519.ic21':'mpr-16519.21','mpr-16525.ic18':'mpr-16525.18','mpr-16520.ic22':'mpr-16520.22','mpr-16772.ic19':'mpr-16772.19','mpr-16771.ic23':'mpr-16771.23'}.items(): s = s.replace(old,new)
    p.write_text(s)
    p = Path('source/scripts/recompile.py'); s = p.read_text()
    if platform == 'ios':
        s = s.replace('run(build_cmd + ["--parallel"])', 'print("Native code generated; iOS build next")')
    else:
        s = s.replace('run(build_cmd + ["--parallel"])', 'run(build_cmd + ["--target", "daytona", "--parallel", "2"])')
    p.write_text(s)
    if platform == 'ios':
        # Replace only the validation icon pixels; never rerun source patches.
        icon_dir = Path('source/platform/mobile/ios/Assets.xcassets/AppIcon.appiconset')
        import json
        specs = json.loads((icon_dir / 'Contents.json').read_text())['images']
        for entry in specs:
            pixels = int(float(entry['size'].split('x')[0]) * float(entry['scale'][:-1]))
            run(['sips', '-z', str(pixels), str(pixels), 'private-input/daytona-official-art-icon-white-1024.png', '--out', str(icon_dir / entry['filename'])])
        run(['cmake','-S','.','-B','build-daytona','-G','Ninja','-DCMAKE_BUILD_TYPE=Release','-DM2_ROMSET=daytona'],cwd='source')
    else:
        run(['cmake','-S','.','-B','build-daytona','-A','x64','-T','ClangCL','-DM2_ROMSET=daytona'],cwd='source')
    run([sys.executable,'scripts/recompile.py','--set','daytona','--build-dir','build-daytona'],cwd='source')
    if platform == 'ios':
        gen = str(Path('source/build-daytona/gen').resolve())
        run(['cmake','-S','.','-B','build-ios-check','-G','Xcode','-DCMAKE_SYSTEM_NAME=iOS','-DCMAKE_OSX_ARCHITECTURES=arm64','-DCMAKE_OSX_DEPLOYMENT_TARGET=15.0','-DM2_ROMSET=daytona','-DM2_GEN_ROOT='+gen,'-DCMAKE_XCODE_ATTRIBUTE_CODE_SIGNING_ALLOWED=NO','-DCMAKE_XCODE_ATTRIBUTE_CODE_SIGNING_REQUIRED=NO','-DCMAKE_XCODE_ATTRIBUTE_CODE_SIGN_IDENTITY='],cwd='source')
        run(['cmake','--build','build-ios-check','--config','Release','--target','daytona','--parallel','3'],cwd='source')
        app = 'source/build-ios-check/Release-iphoneos/daytona.app'
        run([sys.executable,'verify_ipa.py',app])
        payload = package / 'Payload'; payload.mkdir(exist_ok=True)
        run(['ditto','--norsrc','--noextattr','--noqtn',app,str(payload/'daytona.app')])
        # No signing identity is used. Remove an ad-hoc signature if present.
        signed = subprocess.run(['codesign','-d',str(payload/'daytona.app')],stdout=log,stderr=log).returncode == 0
        if signed: run(['codesign','--remove-signature',str(payload/'daytona.app')])
        run(['ditto','-c','-k','--norsrc','--noextattr','--noqtn','--keepParent','Payload','Daytona-iOS-build8-rumble-warmup-unsigned.ipa'],cwd=str(package))
        run([sys.executable, 'verify_ios_quit_binary.py', str(package/'Daytona-iOS-build8-rumble-warmup-unsigned.ipa')])
        shutil.rmtree(payload)
    else:
        shutil.copyfile('source/build-daytona/Release/daytona.exe', package/'daytona.exe')
    for n in ('LICENSE','THIRD_PARTY.md'): shutil.copyfile(Path('source')/n,package/n)
    (package/'BUILD_SUCCESS.txt').write_text('Build and static package verification passed. Physical display/controller verification is not claimed.\n')
    print('Private game build completed; package will be encrypted')
except Exception:
    print('Private game build failed; details are in the encrypted log artifact')
    sys.exit(1)
finally:
    log.close()

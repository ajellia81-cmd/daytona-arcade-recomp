from pathlib import Path
import plistlib
import subprocess
import sys

app = Path(sys.argv[1])
info = plistlib.loads((app / 'Info.plist').read_bytes())
assert info['CFBundleIdentifier'] == 'com.boucydesigns.daytona'
assert info['CADisableMinimumFrameDurationOnPhone'] is True
assert info['UIFileSharingEnabled'] is True
assert info['CFBundleShortVersionString'] == '0.5'
assert info.get('NSLocalNetworkUsageDescription')
assert info.get('CFBundleIcons')
binary = app / info['CFBundleExecutable']
archs = subprocess.check_output(['lipo', '-archs', str(binary)], text=True).strip()
assert archs == 'arm64', archs
strings = subprocess.check_output(['strings', str(binary)], text=True)
for marker in ('daytona.pacing.minimum_duration', 'daytona.pacing.probe',
               'Hardware VRR not verified', 'daytona-pacing.csv',
               'Sync to display (60 fps, +4.3% speed)',
               'VRR pacing (iOS native request, experimental)'):
    assert marker in strings, marker
for forbidden in ('VRR pacing (G-Sync / FreeSync)', 'Graphics API (Restart Required)',
                  'Legacy Logitech wheel support (Restart Required)'):
    assert forbidden not in strings, forbidden
print('IPA verified: arm64, bundle identity/version, ProMotion opt-in, telemetry, iOS options; no desktop-only controls')

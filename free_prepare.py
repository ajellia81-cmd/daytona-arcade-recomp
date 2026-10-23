"""Prepare public source validation without any ROM or private icon."""
from pathlib import Path
import os
import struct
import subprocess
import sys
import zlib

platform = sys.argv[1]

def run(*args):
    subprocess.run(args, check=True)

if platform == 'ios':
    # This generic white validation icon has no private or game-derived image.
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>2I5B', 1, 1, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(b'\x00\xff\xff\xff')) + chunk(b'IEND', b'')
    Path('daytona-official-art-icon-white-1024.png').write_bytes(png)
    run(sys.executable, 'customize_ios.py')
run(sys.executable, 'customize_display.py')
if platform == 'ios': run(sys.executable, 'customize_controls.py')
for name in ('customize_color.py', 'customize_gpu_color.py', 'audit_launcher.py'):
    run(sys.executable, name)
if platform == 'ios':
    run(sys.executable, 'customize_ios_pacing.py')
    p = Path('source/platform/mobile/ios/Info.plist.in')
    p.write_text(p.read_text().replace('<string>0.2</string>', '<string>0.5</string>').replace('<string>2</string>', '<string>7</string>'))
run(sys.executable, 'source/scripts/setup.py', '--no-build')
if platform == 'ios': run(sys.executable, 'customize_ios_pacing.py', '--sdl')
print('Public source prepared without ROM or private icon')

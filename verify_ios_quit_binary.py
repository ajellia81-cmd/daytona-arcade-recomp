"""Inspect the real arm64 UIKit entry method's external branch targets."""
import struct
import zipfile
import plistlib
import sys


def inspect(path, delegate="SDLUIKitDelegate"):
    with zipfile.ZipFile(path) as archive:
        info_name = next(n for n in archive.namelist() if n.endswith('/Info.plist') and n.count('/') == 2)
        info = plistlib.loads(archive.read(info_name))
        binary = archive.read(info_name.rsplit('/', 1)[0] + '/' + info['CFBundleExecutable'])
    assert struct.unpack_from('<II', binary) == (0xfeedfacf, 0x100000c)
    sections, symtab, indirect = [], None, None
    offset = 32
    for _ in range(struct.unpack_from('<I', binary, 16)[0]):
        cmd, size = struct.unpack_from('<II', binary, offset)
        if cmd == 0x19:
            for i in range(struct.unpack_from('<I', binary, offset + 64)[0]):
                s = struct.unpack_from('<16s16sQQIIIIIIII', binary, offset + 72 + 80 * i)
                sections.append({'name': s[0].split(b'\0')[0], 'addr': s[2], 'size': s[3], 'offset': s[4], 'flags': s[8], 'indirect_start': s[9], 'stub_size': s[10]})
        elif cmd == 2:
            symtab = struct.unpack_from('<IIII', binary, offset + 8)
        elif cmd == 0xb:
            indirect = struct.unpack_from('<II', binary, offset + 56)
        offset += size
    assert symtab and indirect
    symoff, count, stroff, _ = symtab
    symbols = []
    for i in range(count):
        name_at, kind, section, desc, value = struct.unpack_from('<IBBHQ', binary, symoff + 16 * i)
        at = stroff + name_at
        name = binary[at:binary.index(b'\0', at)].decode(errors='replace')
        symbols.append((name, value, section, kind))
    stubs = {}
    for s in sections:
        if s['flags'] & 0xff != 8:
            continue
        for i in range(s['size'] // s['stub_size']):
            index = struct.unpack_from('<I', binary, indirect[0] + 4 * (s['indirect_start'] + i))[0]
            if index < count:
                stubs[s['addr'] + i * s['stub_size']] = symbols[index][0]
    name, start, section, _ = next(s for s in symbols if s[0] == f'-[{delegate} postFinishLaunch]')
    s = sections[section - 1]
    end = min((sym[1] for sym in symbols if sym[2] == section and sym[1] > start), default=s['addr'] + s['size'])
    calls = []
    for pc in range(start, end, 4):
        word = struct.unpack_from('<I', binary, s['offset'] + pc - s['addr'])[0]
        if word & 0xfc000000 in (0x94000000, 0x14000000):
            imm = word & 0x3ffffff
            if imm & 0x2000000:
                imm -= 0x4000000
            target = pc + imm * 4
            if target in stubs:
                calls.append(stubs[target])
    return {'build': info['CFBundleVersion'], 'method': name, 'exit_call': '_exit' in calls, 'external_calls': calls}


if __name__ == '__main__':
    for path in sys.argv[1:]:
        for delegate in ('SDLUIKitSceneDelegate', 'SDLUIKitDelegate'):
            result = inspect(path, delegate)
            assert result['exit_call'], result
            print('Verified UIKit process exit:', result['method'], 'build', result['build'])

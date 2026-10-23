from pathlib import Path
import json
import subprocess

root = Path('source')
main = root / 'src/app/main.cpp'
text = main.read_text()
draw = 'else app::draw_touch_controls(touch);'
tap = 'in_launcher = touch.down(e.tfinger.touchID, e.tfinger.fingerID, tx, ty);'
assert text.count(draw) == 1 and text.count(tap) == 1, 'Mobile source changed: review patch'
text = text.replace(draw, 'else {} // Controller-only build: no virtual buttons')
text = text.replace(tap, 'in_launcher = e.tfinger.x >= 0.90f && e.tfinger.y <= 0.12f; // Top-right tap opens menu')
main.write_text(text)
assert 'app::draw_touch_controls(touch)' not in text
assert 'touch.down(' not in text

assets = root / 'platform/mobile/ios/Assets.xcassets'
icons = assets / 'AppIcon.appiconset'
icons.mkdir(parents=True, exist_ok=True)
(assets / 'Contents.json').write_text(json.dumps({'info': {'author': 'xcode', 'version': 1}}))
specs = [('iphone', 20, 2), ('iphone', 20, 3), ('iphone', 29, 2), ('iphone', 29, 3),
         ('iphone', 40, 2), ('iphone', 40, 3), ('iphone', 60, 2), ('iphone', 60, 3),
         ('ipad', 20, 1), ('ipad', 20, 2), ('ipad', 29, 1), ('ipad', 29, 2),
         ('ipad', 40, 1), ('ipad', 40, 2), ('ipad', 76, 1), ('ipad', 76, 2),
         ('ipad', 83.5, 2), ('ios-marketing', 1024, 1)]
images = []
for idiom, size, scale in specs:
    pixels = int(size * scale)
    name = f'icon-{idiom}-{size}-{scale}.png'
    subprocess.run(['sips', '-z', str(pixels), str(pixels), 'daytona-official-art-icon-white-1024.png', '--out', str(icons / name)], check=True)
    images.append({'idiom': idiom, 'size': f'{size}x{size}', 'scale': f'{scale}x', 'filename': name})
(icons / 'Contents.json').write_text(json.dumps({'images': images, 'info': {'author': 'xcode', 'version': 1}}, indent=2))

cmake = root / 'CMakeLists.txt'
cmake.write_text(cmake.read_text() + '''
if(IOS AND TARGET daytona)
    target_sources(daytona PRIVATE "${CMAKE_SOURCE_DIR}/platform/mobile/ios/Assets.xcassets")
    set_source_files_properties("${CMAKE_SOURCE_DIR}/platform/mobile/ios/Assets.xcassets" PROPERTIES MACOSX_PACKAGE_LOCATION Resources)
    set_target_properties(daytona PROPERTIES XCODE_ATTRIBUTE_ASSETCATALOG_COMPILER_APPICON_NAME AppIcon)
endif()
''')
plist = root / 'platform/mobile/ios/Info.plist.in'
plist.write_text(plist.read_text().replace('<string>0.1</string>', '<string>0.2</string>').replace('<string>1</string>', '<string>2</string>'))
print('Virtual buttons disabled, top-right menu gesture enabled, approved app icon catalog created')


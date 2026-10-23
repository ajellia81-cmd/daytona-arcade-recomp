"""iOS-only native frame-rate hints, Metal timing request, and measured telemetry."""
from pathlib import Path
import sys
root = Path('source')

def edit(name, old, new, count=1):
    p = root / name
    s = p.read_text()
    assert s.count(old) == count, (name, old, s.count(old))
    p.write_text(s.replace(old, new))

if '--sdl' in sys.argv:
    # setup.py has fetched the pinned SDL commit at this point.
    name = 'extern/sdl3/src/gpu/metal/SDL_gpu_metal.m'
    edit(name, '// Submission\n', '''// Private iOS presentation probe, owned by the app and retained by callbacks.
#ifdef SDL_PLATFORM_IOS
@protocol DaytonaPresentationProbe
- (void)recordTime:(double)time generation:(long long)generation;
@end
#endif

// Submission
''')
    edit(name, '            [metalCommandBuffer->handle presentDrawable:windowData->drawable];', '''#ifdef SDL_PLATFORM_IOS
            const SDL_PropertiesID props = SDL_GetWindowProperties(windowData->window);
            id<DaytonaPresentationProbe> probe = (__bridge id<DaytonaPresentationProbe>)SDL_GetPointerProperty(props, "daytona.pacing.probe", NULL);
            const long long generation = SDL_GetNumberProperty(props, "daytona.pacing.generation", 0);
            if (probe) {
                [windowData->drawable addPresentedHandler:^(id<MTLDrawable> drawable) {
                    [probe recordTime:drawable.presentedTime generation:generation];
                }];
            }
            const double duration = SDL_GetFloatProperty(props, "daytona.pacing.minimum_duration", 0);
            if (duration > 0)
                [metalCommandBuffer->handle presentDrawable:windowData->drawable afterMinimumDuration:duration];
            else
                [metalCommandBuffer->handle presentDrawable:windowData->drawable];
#else
            [metalCommandBuffer->handle presentDrawable:windowData->drawable];
#endif''')
    # Both scene-based (iOS 13+) and legacy delegates invoke SDL_main.
    # Daytona returns only after saving and releasing application resources.
    # Cover both paths; the scene path is used on current iPhones/LiveContainer.
    edit('extern/sdl3/src/video/uikit/SDL_uikitappdelegate.m',
         '    if (launchWindow) {\n        launchWindow.hidden = YES;\n        launchWindow = nil;\n    }',
         '    if (launchWindow) {\n        launchWindow.hidden = YES;\n        launchWindow = nil;\n    }\n#if defined(SDL_PLATFORM_IOS)\n    // Daytona has finished saving and teardown in either UIKit lifecycle.\n    exit(exit_status);\n#endif', count=2)
    print('Pinned SDL: iOS presentation timing and clean process exit added')
    sys.exit(0)

for name in ('ios_pacing.h', 'ios_pacing.mm'):
    (root / 'platform/mobile/ios' / name).write_text((Path(__file__).parent / name).read_text())
edit('CMakeLists.txt', 'target_sources(daytona_app PRIVATE platform/mobile/ios/rom_picker.mm)', 'target_sources(daytona_app PRIVATE platform/mobile/ios/rom_picker.mm platform/mobile/ios/ios_pacing.mm)')
edit('CMakeLists.txt', 'set_source_files_properties(platform/mobile/ios/rom_picker.mm PROPERTIES', 'set_source_files_properties(platform/mobile/ios/rom_picker.mm platform/mobile/ios/ios_pacing.mm PROPERTIES')
edit('src/app/main.cpp', '#include "app/pacing.h"', '#include "app/pacing.h"\n#ifdef SDL_PLATFORM_IOS\n#include "ios_pacing.h"\n#endif')
edit('src/app/pacing.cpp', '#include "app/pacing.h"', '#include "app/pacing.h"\n#if defined(__APPLE__)\n#include <TargetConditionals.h>\n#if TARGET_OS_IOS\n#define DAYTONA_IOS_PACING 1\n#endif\n#endif')
# Clock-based stepping avoids assuming every SDL loop iteration is a vblank.
# In VRR request mode the native helper handles the wait/presentation hint.
edit('src/app/pacing.cpp', 'Pacing choose_pacing(double refresh_hz, const PacingSettings &s) {', '''Pacing choose_pacing(double refresh_hz, const PacingSettings &s) {
#ifdef DAYTONA_IOS_PACING
    (void)refresh_hz;
    return {Pacing::Mode::Clock, 1, s.sync_display && !s.vrr ? 60.0 : kArcadeHz};
#else''')
edit('src/app/pacing.cpp', '    return {Pacing::Mode::Clock, 1, kArcadeHz};\n}', '    return {Pacing::Mode::Clock, 1, kArcadeHz};\n#endif\n}')
edit('src/app/pacing.cpp', 'case Mode::Clock: std::snprintf(s, sizeof s, "the arcade\'s speed, 57.52 frames/s%s", display); break;', '''case Mode::Clock:
        if (std::fabs(game_hz - kArcadeHz) > 0.01)
            std::snprintf(s, sizeof s, "elapsed-time clock, %.2f frames/s (display timing not inferred)%s", game_hz, display);
        else std::snprintf(s, sizeof s, "the arcade's speed, 57.52 frames/s%s", display);
        break;''')
edit('src/app/main.cpp', '        const double refresh = display_refresh();', '''#ifdef SDL_PLATFORM_IOS
        app::ios_pacing_update(window, cfg.pace_vrr ? 2 : cfg.pace_sync_display ? 1 : 0, game && !in_launcher);
        app::ios_pacing_wait();
#endif
        const double refresh = display_refresh();''')
edit('src/app/main.cpp', '        launcher.set_pacing_status(pacer.pacing().describe(refresh));', '''#ifdef SDL_PLATFORM_IOS
        launcher.set_pacing_status(app::ios_pacing_status());
#else
        launcher.set_pacing_status(pacer.pacing().describe(refresh));
#endif''')
edit('src/app/main.cpp', '    SDL_DestroyWindow(window);', '''#ifdef SDL_PLATFORM_IOS
    app::ios_pacing_close();
#endif
    SDL_DestroyWindow(window);''')
# F11 is a desktop shortcut; a hardware keyboard must not un-fullscreen iOS.
edit('src/app/main.cpp', '            else if (e.type == SDL_EVENT_KEY_DOWN && e.key.scancode == SDL_SCANCODE_F11) {', '            else if (e.type == SDL_EVENT_KEY_DOWN && e.key.scancode == SDL_SCANCODE_F11) {\n#ifndef SDL_PLATFORM_IOS')
edit('src/app/main.cpp', '                cfg.save();\n            }\n            if (in_launcher)', '                cfg.save();\n#endif\n            }\n            if (in_launcher)')

p = root / 'src/app/launcher.cpp'
s = p.read_text()
a = s.index('            ImGui::TextUnformatted("Frame pacing");')
b = s.index('            if (ImGui::Checkbox("Skip launcher"', a)
desktop = s[a:b]
s = s[:a] + '#ifndef SDL_PLATFORM_IOS\n' + desktop + '''#else
            ImGui::TextUnformatted("iOS frame pacing (choose one, or leave both off)");
            if (ImGui::Checkbox("Sync to display (60 fps, +4.3% speed)", &cfg_.pace_sync_display)) {
                if (cfg_.pace_sync_display) cfg_.pace_vrr = false;
                cfg_.pace_smooth = false;
                cfg_.save();
            }
            ImGui::TextWrapped("Runs at 60 fps using elapsed time and requests the display's maximum refresh (120 Hz on supported ProMotion screens). iOS may limit the actual rate. Reference audio follows the faster game; native audio keeps its device clock.");
            if (ImGui::Checkbox("VRR pacing (iOS native request, experimental)", &cfg_.pace_vrr)) {
                if (cfg_.pace_vrr) cfg_.pace_sync_display = false;
                cfg_.pace_smooth = false;
                cfg_.save();
            }
            ImGui::TextWrapped("Keeps arcade speed (57.52 fps), requests matching Core Animation timing and Metal minimum presentation duration. ProMotion may round to a supported rate. If presentation falls below target, the app removes the Metal hold and falls back to arcade-clock pacing. This is not G-Sync/FreeSync and does not prove hardware VRR.");
            ImGui::TextWrapped("Now: %s", pacing_status_.c_str());
#endif
''' + s[b:]
p.write_text(s)
edit('platform/mobile/ios/Info.plist.in', '    <key>LSRequiresIPhoneOS</key>', '    <key>CADisableMinimumFrameDurationOnPhone</key>\n    <true/>\n    <key>LSRequiresIPhoneOS</key>')
print('iOS pacing: exclusive selections, native requests, actual Metal timestamps and fallback installed')

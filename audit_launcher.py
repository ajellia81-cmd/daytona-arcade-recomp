"""Patch the pinned private source after existing display/colour patches.

iOS display requests and presentation telemetry are added in a separate patch.
The shader-only pass is also used by the shared shader generation job.
"""
from pathlib import Path
import sys

root = Path('source')

def edit(name, old, new, count=1):
    p = root / name
    s = p.read_text()
    assert s.count(old) == count, (name, old, s.count(old))
    p.write_text(s.replace(old, new))

def guard_block(name, start, end, alternate):
    p = root / name
    s = p.read_text()
    assert s.count(start) == 1 and s.count(end) == 1, (name, start, end)
    a, b = s.index(start), s.index(end)
    assert a < b
    s = s[:a] + '#ifndef SDL_PLATFORM_IOS\n' + s[a:b] + '#else\n' + alternate + '\n#endif\n' + s[b:]
    p.write_text(s)

# Video::palette_w already corrects pens_, which is copied to gpu_pens_.
# CPU foreground_layer() uses those same corrected pens. Only raw 3D
# polygon colours and textures must receive the GPU correction again.
edit('src/app/gpu/m2.hlsl', 'return float4(apply_display_color(c.rgb, i.display_color), 1.0);', 'return float4(c.rgb, 1.0); // CPU layer is already display-corrected')
for expr in ('p', 'tiledata[kTilePens + tile_back(sx, sy)]', 'tiledata[kTilePens + pen]'):
    edit('src/app/gpu/m2.hlsl', f'float4(apply_display_color(pen_color({expr}).rgb, i.display_color), 1.0)', f'pen_color({expr})')
if '--shaders-only' in sys.argv:
    print('Shader audit: CPU tile/HUD correction applied exactly once; GPU 3D correction retained')
    sys.exit(0)

launcher = 'src/app/launcher.cpp'
main = 'src/app/main.cpp'

# Never offer a backend that this OS cannot create.
guard_block(launcher, '            static const char *apis[]', '            static const char *renderers[]',
    '            ImGui::TextDisabled("Graphics API: Metal (iOS backend; no API selection).");')
edit(launcher, 'static const char *apis[] = {"Automatic", "Vulkan", "Direct3D 12", "Metal"};', '#ifdef _WIN32\n            static const char *apis[] = {"Automatic", "Vulkan", "Direct3D 12"};\n            static const char *api_ids[] = {"", "vulkan", "direct3d12"};\n#else\n            static const char *apis[] = {"Automatic", "Vulkan", "Direct3D 12", "Metal"};')
edit(launcher, 'static const char *api_ids[] = {"", "vulkan", "direct3d12", "metal"};', 'static const char *api_ids[] = {"", "vulkan", "direct3d12", "metal"};\n#endif\n            constexpr int api_count = int(sizeof(apis) / sizeof(apis[0]));')
edit(launcher, 'for (int i = 0; i < 4; i++)\n                if (cfg_.gpu', 'for (int i = 0; i < api_count; i++)\n                if (cfg_.gpu')
edit(launcher, '"Graphics API (Restart Required)", &api, apis, 4', '"Graphics API (Restart Required)", &api, apis, api_count')

guard_block(launcher, '            if (ImGui::Checkbox("Fullscreen"', '            ImGui::TextUnformatted("Frame pacing");',
    '            ImGui::TextWrapped("iOS manages the fullscreen window and display mode. Desktop window size, exclusive refresh modes and cursor hiding are unavailable here.");')
# iOS-specific pacing UI and runtime are installed by customize_ios_pacing.py.
edit('src/app/config.cpp', '\n}\n\nvoid Config::save()', '\n    if (pace_vrr) pace_sync_display = pace_smooth = false;\n    else if (pace_sync_display) pace_smooth = false;\n#ifdef SDL_PLATFORM_IOS\n    gpu = "metal";\n    fullscreen = true;\n    fullscreen_mode.clear();\n    hide_cursor = false;\n    pace_smooth = false;\n    legacy_logitech_wheels = false;\n    ffb_invert = false;\n    ffb_centring_override = false;\n#endif\n}\n\nvoid Config::save()')
edit(main, '    if (!cfg.gpu.empty()) SDL_SetHint', '    #ifdef SDL_PLATFORM_IOS\n    cfg.gpu = "metal"; // also override unsupported --gpu arguments\n    #endif\n    if (!cfg.gpu.empty()) SDL_SetHint')
edit(main, '    app::apply_fullscreen_mode(window, cfg.fullscreen_mode);', '#ifndef SDL_PLATFORM_IOS\n    if (!app::apply_fullscreen_mode(window, cfg.fullscreen_mode))\n        std::fprintf(stderr, "daytona: requested fullscreen mode rejected: %s\\n", SDL_GetError());\n#endif')

# Rumble is meaningful on supported controllers; directional wheel motors
# and the desktop Logitech HIDAPI workaround are not iOS features.
edit(launcher, '#ifndef _WIN32 // SDL\'s own Logitech driver is off on Windows already', '#if !defined(_WIN32) && !defined(SDL_PLATFORM_IOS) // Desktop Logitech workaround')
edit(launcher, 'if (ImGui::SliderInt("Force feedback (Experimental)", &ffb', '#ifdef SDL_PLATFORM_IOS\n            const char *force_label = "Controller rumble strength";\n#else\n            const char *force_label = "Force feedback (Experimental)";\n#endif\n            if (ImGui::SliderInt(force_label, &ffb')
edit(launcher, '            ImGui::SameLine();\n            if (ImGui::Checkbox("Invert force", &cfg_.ffb_invert)) cfg_.save();', '#ifndef SDL_PLATFORM_IOS\n            ImGui::SameLine();\n            if (ImGui::Checkbox("Invert force", &cfg_.ffb_invert)) cfg_.save();\n            ImGui::SetItemTooltip("Wheel motor direction only; gamepad rumble has no direction to invert.");\n#endif')
guard_block(launcher, '            ImGui::TextDisabled("The arcade wheel\'s motor', '            if (ImGui::BeginTable("binds"',
    '            ImGui::TextWrapped("Rumble requires a connected controller advertising SDL rumble support. Wheel motor forces, force inversion and legacy Logitech driver selection are unavailable on iOS. Device support: %s.", ffb_device_);\n')

# Accurate instructions for the previously implemented adaptive mobile menu.
edit(launcher, '            ImGui::TextDisabled("(starts the game straight away; Esc opens this launcher)");', '#ifdef SDL_PLATFORM_IOS\n            ImGui::TextWrapped("Starts immediately. Use the touch menu or Controls > Open menu (default R3) to return.");\n#else\n            ImGui::TextDisabled("(starts the game straight away; Esc opens this launcher)");\n#endif')
edit(launcher, '            ImGui::TextDisabled("Hardware renderer: the 3D drawn at 2 to 4 times the original resolution, with\\n"\n                                "sharper textures; the window shows it scaled to fit, which smooths the edges.");', '            ImGui::TextWrapped("Hardware rendering target: Off = original; 2x/3x/4x = integer supersampling; Native display = window drawable pixels; 4K = fixed 3840 x 2160. These do not change the physical display mode. Software uses original resolution. Larger targets cost GPU time and memory.");')
edit(launcher, '"iPhone full screen (device)"', '"Window / device aspect"')
edit(launcher, '            ImGui::TextDisabled("Shared native sequencer/mixer; reference audio remains available for comparison.");', '            ImGui::TextWrapped("Shared native sequencer/mixer; reference audio remains available. Native audio uses the device audio clock, does not speed up with display sync, and currently lacks MultiPCM vibrato (notably linked-play music).");')
edit(launcher, '            if (!cfg_.color_reference() && cfg_.renderer == "hardware")\n                ImGui::TextDisabled("Hardware renderer remains enabled; colour correction is applied where the GPU path can preserve performance.");', '            ImGui::TextWrapped("Colour correction applies once to CPU layers and GPU 3D, including Native display and 4K targets.");')

# Desktop timing remains functional, without asserting driver VRR state.
edit('src/app/pacing.cpp', '"VRR, 57.52 frames/s, each held to 17.38 ms%s"', '"frame timer, 57.52 frames/s, 17.38 ms; driver VRR not verified%s"')
edit(launcher, '"VRR pacing (G-Sync / FreeSync)"', '"VRR frame timer (requires driver VRR)"')
edit(launcher, '"display refreshes at the game\'s rate and every frame is shown for the same time.\\n"', '"driver may present at the game\'s rate. This does not enable or verify hardware VRR.\\n"')
for label, key, others in (
    ('Smooth pacing on a 57.52 Hz display', 'pace_smooth', ('pace_sync_display', 'pace_vrr')),
    ("Sync to display (changes the game's speed)", 'pace_sync_display', ('pace_smooth', 'pace_vrr')),
    ('VRR frame timer (requires driver VRR)', 'pace_vrr', ('pace_smooth', 'pace_sync_display'))):
    edit(launcher, f'if (ImGui::Checkbox("{label}", &cfg_.{key})) cfg_.save();', f'if (ImGui::Checkbox("{label}", &cfg_.{key})) {{\n                if (cfg_.{key}) cfg_.{others[0]} = cfg_.{others[1]} = false;\n                cfg_.save();\n            }}')

# Report rejected SDL requests rather than saving a misleading UI selection.
edit('src/app/launcher.h', 'void apply_fullscreen_mode(', 'bool apply_fullscreen_mode(')
edit(launcher, 'void apply_fullscreen_mode(', 'bool apply_fullscreen_mode(')
edit(launcher, '        SDL_SetWindowFullscreenMode(window, &mode);', '        return SDL_SetWindowFullscreenMode(window, &mode);')
edit(launcher, '        SDL_SetWindowFullscreenMode(window, nullptr); // borderless, at the desktop\'s mode', '        return key.empty() ? SDL_SetWindowFullscreenMode(window, nullptr) : false; // no silent mode fallback')
edit(launcher, '                SDL_SetWindowFullscreen(window_, cfg_.fullscreen);', '                if (!SDL_SetWindowFullscreen(window_, cfg_.fullscreen)) {\n                    error_ = std::string("Fullscreen request rejected: ") + SDL_GetError();\n                    cfg_.fullscreen = !cfg_.fullscreen;\n                }')
edit(launcher, '                    cfg_.fullscreen_mode = key;\n                    apply_fullscreen_mode(window_, key);\n                    cfg_.save();', '                    if (apply_fullscreen_mode(window_, key)) {\n                        cfg_.fullscreen_mode = key;\n                        cfg_.save();\n                    } else error_ = std::string("Display mode request rejected: ") + SDL_GetError();')
edit(launcher, 'void apply_window_size(', 'bool apply_window_size(')
edit(launcher, '        SDL_SetWindowSize(window, w, h);', '        return SDL_SetWindowSize(window, w, h);\n    return false;')
edit(launcher, '                    cfg_.window_size = window_sizes[window_size];\n                    apply_window_size(window_, cfg_.window_size);\n                    cfg_.save();', '                    if (apply_window_size(window_, window_sizes[window_size])) {\n                        cfg_.window_size = window_sizes[window_size];\n                        cfg_.save();\n                    } else error_ = std::string("Window size request rejected: ") + SDL_GetError();')
edit(main, '    app::Launcher launcher(cfg, window);', '    app::Launcher launcher(cfg, window);\n    if (!gpu.ok()) launcher.set_error("Hardware renderer unavailable; software fallback: " + gpu.error());')
edit(main, '                    native_w = target_w; native_h = target_h; hires_scale = 0; hires_levels = 1;', '                    native_w = target_w; native_h = target_h; hires_scale = 0; hires_levels = 1;\n                    if (!hires) { launcher.set_error(std::string("Requested render target unavailable; original resolution fallback: ") + SDL_GetError()); cfg.supersampling = 1; cfg.save(); }')

plist = root / 'platform/mobile/ios/Info.plist.in'
s = plist.read_text()
assert '<key>NSLocalNetworkUsageDescription</key>' not in s
s = s.replace('    <key>LSRequiresIPhoneOS</key>', '    <key>NSLocalNetworkUsageDescription</key>\n    <string>Connect to other Daytona cabinets for optional local network link play.</string>\n    <key>LSRequiresIPhoneOS</key>')
plist.write_text(s)
edit(main, '                if (!hires) std::fprintf(stderr, "daytona: %dx super sampling unavailable: %s\\n", scale, SDL_GetError());', '                if (!hires) { launcher.set_error(std::string("Supersampling unavailable; original resolution fallback: ") + SDL_GetError()); cfg.supersampling = 1; cfg.save(); }')
print('Launcher/runtime platform audit applied; desktop controls preserved')

# Adapt the upstream cap test to this private build's existing wider view cap.
edit('tests/test_app_config.cpp', 'check(loaded.aspect_ratio() == 21.0 / 9.0, "saved future aspect is capped at the supported view");', 'check(loaded.aspect_ratio() == app::Config::kMaxAspect, "saved future aspect is capped at the supported view");')
edit('tests/test_app_config.cpp', '    return failures ? 1 : 0;', '''    std::istringstream conflict("pace_sync_display=1\\npace_vrr=1\\npace_smooth=1\\n");
    loaded.read(conflict);
    check(loaded.pace_vrr && !loaded.pace_sync_display && !loaded.pace_smooth, "conflicting legacy pacing settings normalize to VRR only");
    std::ostringstream normalized;
    loaded.write(normalized);
    app::Config roundtrip;
    std::istringstream saved(normalized.str());
    roundtrip.read(saved);
    check(roundtrip.pace_vrr && !roundtrip.pace_sync_display, "exclusive pacing selection survives save and reload");
    return failures ? 1 : 0;''')

"""iOS/Metal-only native display mode; original integer-scale modes retained."""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else 'source')
def edit(name, old, new, count=1):
    p = root / name
    s = p.read_text()
    assert s.count(old) == count, (name, old, s.count(old))
    p.write_text(s.replace(old, new))

edit('src/app/config.cpp', 'std::clamp(std::atoi(v.c_str()), 1, 4)', 'std::clamp(std::atoi(v.c_str()), 0, 5)')
edit('src/app/config.h', 'std::string fullscreen_mode;', 'std::string fullscreen_mode;\n    std::string window_size = "1280x960"; // Windows windowed-mode client size')
edit('src/app/config.cpp', 'else if (k == "fullscreen_mode") fullscreen_mode = v;', 'else if (k == "fullscreen_mode") fullscreen_mode = v;\n        else if (k == "window_size") window_size = v;')
edit('src/app/config.cpp', 'f << "fullscreen_mode=" << fullscreen_mode << "\\n";', 'f << "fullscreen_mode=" << fullscreen_mode << "\\n";\n    f << "window_size=" << window_size << "\\n";')
edit('src/app/launcher.cpp', '{"Off", "2x", "3x", "4x"}', '{"Off", "2x", "3x", "4x", "Native display", "4K (3840x2160)"}')
edit('src/app/launcher.cpp', 'int ss = std::clamp(cfg_.supersampling, 1, 4) - 1;', 'int ss = cfg_.supersampling == 0 ? 4 : cfg_.supersampling == 5 ? 5 : std::clamp(cfg_.supersampling, 1, 4) - 1;')
edit('src/app/launcher.cpp', '"Super sampling", &ss, supersampling, 4', '"Rendering resolution", &ss, supersampling, 6')
edit('src/app/launcher.cpp', 'cfg_.supersampling = ss + 1;', 'cfg_.supersampling = ss == 4 ? 0 : ss == 5 ? 5 : ss + 1;')
edit('src/app/launcher.cpp', '''void apply_fullscreen_mode(SDL_Window *window, const std::string &key) {
    int w = 0, h = 0;
    float hz = 0, density = 1;
    SDL_DisplayMode mode;
    if (!key.empty() && std::sscanf(key.c_str(), "%dx%d@%f*%f", &w, &h, &hz, &density) >= 3 &&
        SDL_GetClosestFullscreenDisplayMode(SDL_GetDisplayForWindow(window), w, h, hz, density > 1, &mode))
        SDL_SetWindowFullscreenMode(window, &mode);
    else
        SDL_SetWindowFullscreenMode(window, nullptr); // borderless, at the desktop's mode
}''', '''void apply_fullscreen_mode(SDL_Window *window, const std::string &key) {
    int w = 0, h = 0;
    float hz = 0, density = 1;
    SDL_DisplayMode mode;
    if (!key.empty() && std::sscanf(key.c_str(), "%dx%d@%f*%f", &w, &h, &hz, &density) >= 3 &&
        SDL_GetClosestFullscreenDisplayMode(SDL_GetDisplayForWindow(window), w, h, hz, density > 1, &mode))
        SDL_SetWindowFullscreenMode(window, &mode);
    else
        SDL_SetWindowFullscreenMode(window, nullptr); // borderless, at the desktop's mode
}

#ifdef _WIN32
void apply_window_size(SDL_Window *window, const std::string &key) {
    int w = 0, h = 0;
    if (std::sscanf(key.c_str(), "%dx%d", &w, &h) == 2 &&
        w >= 640 && h >= 480 && w <= 7680 && h <= 4320)
        SDL_SetWindowSize(window, w, h);
}
#endif''')
edit('src/app/launcher.cpp', '{"Original (4:3)", "16:10", "16:9", "21:9"}', '{"Original (4:3)", "16:10", "16:9", "21:9", "iPhone full screen (device)"}')
edit('src/app/launcher.cpp', '{"", "16:10", "16:9", "21:9"}', '{"", "16:10", "16:9", "21:9", "display"}')
edit('src/app/launcher.cpp', 'for (int i = 0; i < 4; i++)\n                if (cfg_.aspect', 'for (int i = 0; i < 5; i++)\n                if (cfg_.aspect')
edit('src/app/launcher.cpp', '"Widescreen", &aspect, aspects, 4', '"Widescreen", &aspect, aspects, 5')
edit('src/app/launcher.cpp', '''            ImGui::SetItemTooltip("No mouse cursor while the game plays. It shows again whenever this\\n"
                                  "launcher opens (Esc), and hides again on Resume.");
            {   // exclusive fullscreen: the display's own modes, a custom 57.52 Hz one among them''', '''            ImGui::SetItemTooltip("No mouse cursor while the game plays. It shows again whenever this\\n"
                                  "launcher opens (Esc), and hides again on Resume.");
#ifdef _WIN32
            if (!cfg_.fullscreen) {
                static const char *window_labels[] = {"960 x 720 (4:3)", "1280 x 720 (16:9)", "1280 x 960 (4:3)", "1600 x 900 (16:9)", "1600 x 1200 (4:3)", "1920 x 1080 (16:9)", "1920 x 1440 (4:3)", "2560 x 1440 (16:9)", "3200 x 1800 (16:9)", "3840 x 2160 (16:9)"};
                static const char *window_sizes[]  = {"960x720", "1280x720", "1280x960", "1600x900", "1600x1200", "1920x1080", "1920x1440", "2560x1440", "3200x1800", "3840x2160"};
                int window_size = 2;
                for (int i = 0; i < 10; ++i) if (cfg_.window_size == window_sizes[i]) window_size = i;
                ImGui::SetNextItemWidth(200);
                if (ImGui::Combo("Window size", &window_size, window_labels, 10)) {
                    cfg_.window_size = window_sizes[window_size];
                    apply_window_size(window_, cfg_.window_size);
                    cfg_.save();
                }
                ImGui::SetItemTooltip("Changes the windowed client size immediately. Native display follows this size.");
            }
#endif
            {   // exclusive fullscreen: the display's own modes, a custom 57.52 Hz one among them''')
edit('src/app/launcher.cpp', '''            if (ImGui::Checkbox("Fullscreen", &cfg_.fullscreen)) {
                SDL_SetWindowFullscreen(window_, cfg_.fullscreen);
                cfg_.save();
            }''', '''            if (ImGui::Checkbox("Fullscreen", &cfg_.fullscreen)) {
                SDL_SetWindowFullscreen(window_, cfg_.fullscreen);
#ifdef _WIN32
                if (!cfg_.fullscreen) apply_window_size(window_, cfg_.window_size);
#endif
                cfg_.save();
            }''')
edit('src/app/config.h', 'kMaxAspect = 21.0 / 9.0', 'kMaxAspect = 3.0')
# Default only on new installs: existing preferences remain user-controlled.
edit('src/app/config.h', 'std::string aspect;', 'std::string aspect = "display";')
edit('src/app/config.h', 'int supersampling = 1;', 'int supersampling = 0;')
edit('src/app/main.cpp', '''SDL_Window *window = SDL_CreateWindow("Daytona USA", W * 2, H * 2,
                                          SDL_WINDOW_RESIZABLE | (cfg.fullscreen ? SDL_WINDOW_FULLSCREEN : 0));''', '''int window_w = W * 2, window_h = H * 2;
#ifdef _WIN32
    if (std::sscanf(cfg.window_size.c_str(), "%dx%d", &window_w, &window_h) != 2 ||
        window_w < 640 || window_h < 480 || window_w > 7680 || window_h > 4320)
        window_w = W * 2, window_h = H * 2;
#endif
    SDL_Window *window = SDL_CreateWindow("Daytona USA", window_w, window_h,
                                          SDL_WINDOW_RESIZABLE | (cfg.fullscreen ? SDL_WINDOW_FULLSCREEN : 0));''')
edit('src/app/main.cpp', 'SDL_WINDOW_RESIZABLE | (cfg.fullscreen', 'SDL_WINDOW_RESIZABLE | SDL_WINDOW_HIGH_PIXEL_DENSITY | (cfg.fullscreen')
edit('src/app/main.cpp', 'game->set_aspect(cfg.aspect_ratio());', '''int display_w = 0, display_h = 0;
            SDL_GetWindowSizeInPixels(window, &display_w, &display_h);
            game->set_aspect(cfg.aspect == "display" && display_h > 0
                ? std::min(double(display_w) / display_h, app::Config::kMaxAspect) : cfg.aspect_ratio());''')
edit('src/app/main.cpp', 'int shown_scale = 1;', 'int shown_scale = 1;\n    int native_w = 0, native_h = 0;\n    bool shown_native = false;')
edit('src/app/main.cpp', 'const int scale = std::clamp(cfg.supersampling, 1, 4);', '''int pixel_w = 0, pixel_h = 0;
            SDL_GetWindowSizeInPixels(window, &pixel_w, &pixel_h);
            const bool fixed_4k = cfg.supersampling == 5;
            const bool native = (cfg.supersampling == 0 || fixed_4k) && pixel_w > 0 && pixel_h > 0;
            if (native) {
                const int target_w = fixed_4k ? 3840 : pixel_w;
                const int target_h = fixed_4k ? 2160 : pixel_h;
                if (target_w != native_w || target_h != native_h || hires_scale != 0 || !hires) {
                    if (hires) SDL_ReleaseGPUTexture(dev, hires);
                    SDL_GPUTextureCreateInfo hi = ti;
                    hi.width = Uint32(target_w); hi.height = Uint32(target_h); hi.num_levels = 1;
                    hires = SDL_CreateGPUTexture(dev, &hi);
                    native_w = target_w; native_h = target_h; hires_scale = 0; hires_levels = 1;
                    std::printf("daytona: render target %dx%d\\n", target_w, target_h);
                }
                if (hires) {
                    gpu.render(cmd, hires, screen_w, H, game->board().video(),
                               {cfg.color_saturation, cfg.color_gamma, cfg.color_contrast}, 1, native_w, native_h);
                    shown = hires; shown_scale = 1; shown_native = true;
                } else {
                    gpu.render(cmd, screen, screen_w, H, game->board().video());
                    shown = screen; shown_scale = 1; shown_native = false;
                }
            } else {
            shown_native = false;
            const int scale = std::clamp(cfg.supersampling, 1, 4);''')
edit('src/app/main.cpp', '            new_frame = false;\n        }\n        if (new_frame)', '            }\n            new_frame = false;\n        }\n        if (new_frame)')
edit('src/app/main.cpp', 'shown = screen, shown_scale = 1;', 'shown = screen, shown_scale = 1; shown_native = false;', 2)
edit('src/app/main.cpp', 'const Uint32 dw = Uint32(screen_w * scale), dh = Uint32(H * scale);', 'const Uint32 dw = cfg.aspect == "display" ? sw : Uint32(screen_w * scale);\n                const Uint32 dh = cfg.aspect == "display" ? sh : Uint32(H * scale);')
edit('src/app/main.cpp', 'Uint32(screen_w * shown_scale) >> level', 'shown_native ? Uint32(native_w) : Uint32(screen_w * shown_scale) >> level')
edit('src/app/main.cpp', 'Uint32(H * shown_scale) >> level', 'shown_native ? Uint32(native_h) : Uint32(H * shown_scale) >> level')

gp = 'src/app/gpu/'
edit(gp+'gpu_renderer.h', 'int scale = 1);', 'int scale = 1, int target_w = 0, int target_h = 0);')
edit(gp+'gpu_renderer.h', 'int scale, uint32_t vert_bytes);', 'int target_w, int target_h, uint32_t vert_bytes);')
edit(gp+'gpu_renderer.h', 'int h, int scale);', 'int h, double scale);')
edit(gp+'gpu_renderer.cpp', 'int h, int scale, uint32_t vert_bytes)', 'int h, int target_w, int target_h, uint32_t vert_bytes)')
for old, new, n in [('w * scale != depth_w_', 'target_w != depth_w_', 1), ('h * scale != depth_h_', 'target_h != depth_h_', 1), ('Uint32(w * scale)', 'Uint32(target_w)', 1), ('Uint32(h * scale)', 'Uint32(target_h)', 1), ('depth_w_ = w * scale, depth_h_ = h * scale;', 'depth_w_ = target_w, depth_h_ = target_h;', 1)]:
    edit(gp+'gpu_renderer.cpp', old, new, n)
edit(gp+'gpu_renderer.cpp', 'int h, int scale) {', 'int h, double scale) {')
edit(gp+'gpu_renderer.cpp', '                         int scale) {', '                         int scale, int target_w, int target_h) {')
edit(gp+'gpu_renderer.cpp', '    build(video, w, h, scale);', '''    const bool native = target_w > 0 && target_h > 0;
    if (!native) target_w = w * scale, target_h = h * scale;
    const double sx = double(target_w) / w, sy = double(target_h) / h;
    build(video, w, h, std::min(sx, sy));''')
edit(gp+'gpu_renderer.cpp', 'ensure(w, h, scale, vert_bytes)', 'ensure(w, h, target_w, target_h, vert_bytes)')
edit(gp+'gpu_renderer.cpp', 'tiledata_words_[2] = uint32_t(scale);', 'tiledata_words_[2] = uint32_t(scale);\n    tiledata_words_[3] = native ? uint32_t(target_w) : 0;\n    tiledata_words_[4] = native ? uint32_t(target_h) : 0;')
edit(gp+'gpu_renderer.cpp', 'float(w * scale), float(h * scale)', 'float(target_w), float(target_h)')
edit(gp+'gpu_renderer.cpp', 'const SDL_Rect full{0, 0, w * scale, h * scale};', 'const SDL_Rect full{0, 0, target_w, target_h};')
edit(gp+'gpu_renderer.cpp', 'const SDL_Rect clip{b.clip.x * scale, b.clip.y * scale, b.clip.w * scale, b.clip.h * scale};', '''const int x0 = int(std::floor(b.clip.x * sx)), y0 = int(std::floor(b.clip.y * sy));
            const int x1 = int(std::ceil((b.clip.x + b.clip.w) * sx));
            const int y1 = int(std::ceil((b.clip.y + b.clip.h) * sy));
            const SDL_Rect clip{x0, y0, x1 - x0, y1 - y0};''')
# Native-pixel tile coordinates are compiled from m2.hlsl by customize_gpu_color.py
# in the shared shader job, so this script never relies on generated MSL IDs.
print('Full-screen aspect and exact native-pixel render target added')


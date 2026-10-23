"""Optional display colour controls for the private Windows/iOS build.

This deliberately patches presentation after the Model 2 palette/luma/gamma
path.  The 1.00 defaults take a bit-exact fast path.  Non-default controls
select the CPU reference renderer so textured pixels are never only partly
corrected by the experimental GPU path.
"""
from pathlib import Path

root = Path("source")

def edit(name, old, new, count=1):
    path = root / name
    text = path.read_text(encoding="utf-8")
    if old not in text and name == "src/app/config.h":
        old, new = old.replace("= 0;", "= 1;"), new.replace("= 0;", "= 1;")
    if old not in text and name == "src/app/config.cpp":
        old = old.replace(", 0, 5)", ", 1, 4)")
    assert text.count(old) == count, (name, old, text.count(old))
    path.write_text(text.replace(old, new), encoding="utf-8")

(root / "src/runtime/display_color.h").write_text(r'''// Optional presentation correction, after the Model 2 translation/gamma path.
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
namespace rt {
struct DisplayColor {
    float saturation = 1.0f;
    float gamma = 1.0f;
    float contrast = 1.0f;
    uint32_t apply(uint32_t r, uint32_t g, uint32_t b) const {
        if (saturation == 1.0f && gamma == 1.0f && contrast == 1.0f)
            return 0xff000000u | (r << 16) | (g << 8) | b;
        float rf = r / 255.0f, gf = g / 255.0f, bf = b / 255.0f;
        const float y = 0.2126f * rf + 0.7152f * gf + 0.0722f * bf;
        rf = y + (rf - y) * saturation;
        gf = y + (gf - y) * saturation;
        bf = y + (bf - y) * saturation;
        const float exponent = 1.0f / std::max(gamma, 0.01f);
        auto channel = [&](float v) { return uint32_t(std::lround(std::pow(std::clamp((v - 0.5f) * contrast + 0.5f, 0.0f, 1.0f), exponent) * 255.0f)); };
        return 0xff000000u | (channel(rf) << 16) | (channel(gf) << 8) | channel(bf);
    }
};
} // namespace rt
''', encoding="utf-8")

edit("src/runtime/raster.h", '#include "runtime/geo.h"', '#include "runtime/geo.h"\n#include "runtime/display_color.h"')
edit("src/runtime/raster.h", '    Raster();', '    Raster();\n    void set_display_color(const DisplayColor &color) { color_ = color; }')
edit("src/runtime/raster.h", '    uint8_t gamma_[256];', '    uint8_t gamma_[256];\n    DisplayColor color_{};')
edit("src/runtime/video.h", '#include "runtime/raster.h"', '#include "runtime/raster.h"\n#include "runtime/display_color.h"')
edit("src/runtime/video.h", '    Video(const uint8_t *tile_ram, const uint8_t *char_ram);', '''    Video(const uint8_t *tile_ram, const uint8_t *char_ram);
    void set_display_color(const DisplayColor &color) {
        if (color.saturation == color_.saturation && color.gamma == color_.gamma && color.contrast == color_.contrast) return;
        color_ = color; raster_.set_display_color(color); palette_dirty_ = true;
    }
    const DisplayColor &display_color() const { return color_; }''')
edit("src/runtime/video.h", '    uint8_t gamma_[256];', '    uint8_t gamma_[256];\n    DisplayColor color_{};')
edit("src/runtime/video.cpp", 'const uint32_t pen = rgb(gamma_[r], gamma_[g], gamma_[b]);', 'const uint32_t pen = color_.apply(gamma_[r], gamma_[g], gamma_[b]);')
edit("src/runtime/raster.cpp", 'entry.colors[t] = rgb(gamma_[le16(mem_->colorxlat, cr + luma) & 0xff],', 'entry.colors[t] = color_.apply(gamma_[le16(mem_->colorxlat, cr + luma) & 0xff],')
edit("src/runtime/raster.cpp", 'const u32 c = rgb(tr, tg, tb);', 'const u32 c = color_.apply(tr, tg, tb);')
edit("src/runtime/raster.cpp", 'p[x] = rgb(tr, tg, tb);', 'p[x] = color_.apply(tr, tg, tb);')

edit("src/app/config.h", '    int supersampling = 0;', '''    int supersampling = 0;
    float color_saturation = 1.0f;
    float color_gamma = 1.0f;
    float color_contrast = 1.0f;
    bool color_reference() const { return color_saturation == 1.0f && color_gamma == 1.0f && color_contrast == 1.0f; }''')
edit("src/app/config.cpp", 'else if (k == "supersampling") supersampling = std::clamp(std::atoi(v.c_str()), 0, 5);', '''else if (k == "supersampling") supersampling = std::clamp(std::atoi(v.c_str()), 0, 5);
        else if (k == "color_saturation") color_saturation = std::clamp(std::strtof(v.c_str(), nullptr), 0.0f, 2.0f);
        else if (k == "color_gamma") color_gamma = std::clamp(std::strtof(v.c_str(), nullptr), 0.5f, 2.5f);
        else if (k == "color_contrast") color_contrast = std::clamp(std::strtof(v.c_str(), nullptr), 0.5f, 2.0f);''')
edit("src/app/config.cpp", 'f << "supersampling=" << supersampling << "\\n";', '''f << "supersampling=" << supersampling << "\\n";
    f << "color_saturation=" << color_saturation << "\\n";
    f << "color_gamma=" << color_gamma << "\\n";
    f << "color_contrast=" << color_contrast << "\\n";''')
edit("src/app/launcher.cpp", '            ImGui::Spacing();\n            ImGui::Separator();\n            ImGui::TextUnformatted("Enhancements");', '''            ImGui::Spacing();
            ImGui::TextUnformatted("Display colour (optional)");
            bool colour_changed = false;
            ImGui::SetNextItemWidth(200);
            colour_changed |= ImGui::SliderFloat("Saturation", &cfg_.color_saturation, 0.0f, 2.0f, "%.2f");
            ImGui::SetNextItemWidth(200);
            colour_changed |= ImGui::SliderFloat("Gamma", &cfg_.color_gamma, 0.5f, 2.5f, "%.2f");
            ImGui::SetNextItemWidth(200);
            colour_changed |= ImGui::SliderFloat("Contrast", &cfg_.color_contrast, 0.5f, 2.0f, "%.2f");
            if (ImGui::Button("Reset display colour")) cfg_.color_saturation = cfg_.color_gamma = cfg_.color_contrast = 1.0f, colour_changed = true;
            if (colour_changed) cfg_.save();
            ImGui::TextDisabled("Default 1.00 values preserve Model 2/MAME output. This is personal display correction.");
            if (!cfg_.color_reference() && cfg_.renderer == "hardware")
                ImGui::TextDisabled("Hardware renderer remains enabled; colour correction is applied where the GPU path can preserve performance.");
            ImGui::Spacing();
            ImGui::Separator();
            ImGui::TextUnformatted("Enhancements");''')
edit("src/app/main.cpp", '            game->set_hud_edges(cfg.hud_edges);', '            game->board().video().set_display_color({cfg.color_saturation, cfg.color_gamma, cfg.color_contrast});\n            game->set_hud_edges(cfg.hud_edges);')
edit("src/app/main.cpp", 'game->board().video().set_external_3d(cfg.renderer == "hardware" && gpu.ok(), true);', 'game->board().video().set_external_3d(cfg.renderer == "hardware" && gpu.ok() , true);')
print("Optional display colour correction added")


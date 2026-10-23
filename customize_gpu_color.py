"""Use the vertex ScreenUBO for GPU display-colour correction on every backend.

Fragment uniform counts stay unchanged: Metal otherwise relocates storage-buffer
bindings when switching pipelines, causing corrupted iOS frames.
"""
from pathlib import Path
root = Path("source")
def edit(name, old, new, count=1):
    path = root / name
    text = path.read_text(encoding="utf-8")
    actual = text.count(old)
    assert actual == count, (name, actual, old)
    path.write_text(text.replace(old, new), encoding="utf-8")


def edit_either(name, replacements):
    """Apply precisely one source variant (desktop or the iOS native mode)."""
    path = root / name
    text = path.read_text(encoding="utf-8")
    matches = [(old, new) for old, new in replacements if text.count(old) == 1]
    assert len(matches) == 1, (name, [(old, text.count(old)) for old, _ in replacements])
    old, new = matches[0]
    path.write_text(text.replace(old, new), encoding="utf-8")


def edit_if_present(name, old, new):
    path = root / name
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    assert count in (0, 1), (name, count, old)
    if count:
        path.write_text(text.replace(old, new), encoding="utf-8")


def edit_one_or_two(name, old, new):
    """The shared source has one final screen call; iOS native has two."""
    path = root / name
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    assert count in (1, 2), (name, count, old)
    path.write_text(text.replace(old, new), encoding="utf-8")
edit("src/app/gpu/m2.hlsl", "struct Screen { float2 size; float2 pad; }; // the render target, in pixels", """struct Screen { float2 size; float2 pad; float4 display_color; }; // target pixels and presentation correction

// This remains in the existing vertex uniform block so every fragment
// pipeline retains the same Metal resource layout.
float3 apply_display_color(float3 c, float3 display_color) {
    if (display_color.x == 1.0 && display_color.y == 1.0 && display_color.z == 1.0) return c;
    const float y = dot(c, float3(0.2126, 0.7152, 0.0722));
    c = y.xxx + (c - y.xxx) * display_color.x;
    c = saturate((c - 0.5) * display_color.z + 0.5);
    return pow(c, 1.0 / max(display_color.y, 0.01));
}""")
edit("src/app/gpu/m2.hlsl", "    nointerpolation uint2 more : TEXCOORD3;\n};", "    nointerpolation uint2 more : TEXCOORD3;\n    nointerpolation float3 display_color : TEXCOORD4;\n};")
edit("src/app/gpu/m2.hlsl", "    o.more = i.more;\n    return o;", "    o.more = i.more;\n    o.display_color = screen.display_color.xyz;\n    return o;")
edit("src/app/gpu/m2.hlsl", "if (renderer < 2u) return i.color; // solid: its palette colour, from the CPU", "if (renderer < 2u) return float4(apply_display_color(i.color.rgb, i.display_color), i.color.a); // solid: its palette colour, from the CPU")
edit("src/app/gpu/m2.hlsl", "return float4(float(xlat[cr + luma]) / 255.0, float(xlat[cg + luma]) / 255.0, float(xlat[cb + luma]) / 255.0, 1.0);", "return float4(apply_display_color(float3(float(xlat[cr + luma]) / 255.0, float(xlat[cg + luma]) / 255.0, float(xlat[cb + luma]) / 255.0), i.display_color), 1.0);")
edit("src/app/gpu/m2.hlsl", "    float2 uv : TEXCOORD0;\n};", "    float2 uv : TEXCOORD0;\n    nointerpolation float3 display_color : TEXCOORD1;\n};")
edit("src/app/gpu/m2.hlsl", "    o.uv = i.uv;\n    return o;", "    o.uv = i.uv;\n    o.display_color = screen.display_color.xyz;\n    return o;")
edit("src/app/gpu/m2.hlsl", """    const int scale = int(tiledata[2]);
    const int out_w = kTileW + 2 * margin;
    const int x = int(i.pos.x) / scale - margin, y = int(i.pos.y) / scale;""", """    const int scale = int(tiledata[2]);
    const int out_w = kTileW + 2 * margin;
    const int native_w = int(tiledata[3]), native_h = int(tiledata[4]);
    const int raster_x = native_w > 0 ? min(int(i.pos.x * float(out_w) / float(native_w)), out_w - 1) : int(i.pos.x) / scale;
    const int raster_y = native_h > 0 ? min(int(i.pos.y * float(kTileH) / float(native_h)), kTileH - 1) : int(i.pos.y) / scale;
    const int x = raster_x - margin, y = raster_y;""")
edit("src/app/gpu/m2.hlsl", """    const int scale = int(tiledata[2]);
    const int x = int(i.pos.x) / scale - int(tiledata[0]), y = int(i.pos.y) / scale;""", """    const int scale = int(tiledata[2]);
    const int margin = int(tiledata[0]);
    const int out_w = kTileW + 2 * margin;
    const int native_w = int(tiledata[3]), native_h = int(tiledata[4]);
    const int raster_x = native_w > 0 ? min(int(i.pos.x * float(out_w) / float(native_w)), out_w - 1) : int(i.pos.x) / scale;
    const int raster_y = native_h > 0 ? min(int(i.pos.y * float(kTileH) / float(native_h)), kTileH - 1) : int(i.pos.y) / scale;
    const int x = raster_x - margin, y = raster_y;""")
edit("src/app/gpu/m2.hlsl", "return float4(c.rgb, 1.0);\n}\n\n// The System 24 tilemap layers", "return float4(apply_display_color(c.rgb, i.display_color), 1.0);\n}\n\n// The System 24 tilemap layers")
edit("src/app/gpu/m2.hlsl", "return pen_color(p);", "return float4(apply_display_color(pen_color(p).rgb, i.display_color), 1.0);")
edit("src/app/gpu/m2.hlsl", "return pen_color(tiledata[kTilePens + tile_back(sx, sy)]);", "return float4(apply_display_color(pen_color(tiledata[kTilePens + tile_back(sx, sy)]).rgb, i.display_color), 1.0);")
edit("src/app/gpu/m2.hlsl", "if (tile_layer(l, false, x, y, pen)) return pen_color(tiledata[kTilePens + pen]);", "if (tile_layer(l, false, x, y, pen)) return float4(apply_display_color(pen_color(tiledata[kTilePens + pen]).rgb, i.display_color), 1.0);")
edit_either("src/app/gpu/gpu_renderer.h", (
    ("void render(SDL_GPUCommandBuffer *cmd, SDL_GPUTexture *target, int w, int h, const rt::Video &video, int scale = 1);",
     "void render(SDL_GPUCommandBuffer *cmd, SDL_GPUTexture *target, int w, int h, const rt::Video &video, const rt::DisplayColor &color, int scale = 1);"),
    ("void render(SDL_GPUCommandBuffer *cmd, SDL_GPUTexture *target, int w, int h, const rt::Video &video, int scale = 1, int target_w = 0, int target_h = 0);",
     "void render(SDL_GPUCommandBuffer *cmd, SDL_GPUTexture *target, int w, int h, const rt::Video &video, const rt::DisplayColor &color, int scale = 1, int target_w = 0, int target_h = 0);"),
))
edit_either("src/app/gpu/gpu_renderer.cpp", (
    ("void GpuRenderer::render(SDL_GPUCommandBuffer *cmd, SDL_GPUTexture *target, int w, int h, const rt::Video &video,\n                         int scale) {",
     "void GpuRenderer::render(SDL_GPUCommandBuffer *cmd, SDL_GPUTexture *target, int w, int h, const rt::Video &video,\n                         const rt::DisplayColor &color, int scale) {"),
    ("void GpuRenderer::render(SDL_GPUCommandBuffer *cmd, SDL_GPUTexture *target, int w, int h, const rt::Video &video,\n                         int scale, int target_w, int target_h) {",
     "void GpuRenderer::render(SDL_GPUCommandBuffer *cmd, SDL_GPUTexture *target, int w, int h, const rt::Video &video,\n                         const rt::DisplayColor &color, int scale, int target_w, int target_h) {"),
))
edit("src/app/gpu/gpu_renderer.cpp", "    const float screen[4] = {fw, fh, 0, 0};", "    const float screen[8] = {fw, fh, 0, 0, color.saturation, color.gamma, color.contrast, 0};")
edit("src/app/main.cpp", "gpu.render(cmd, hires, screen_w, H, game->board().video(), scale);", "gpu.render(cmd, hires, screen_w, H, game->board().video(),\n                           {cfg.color_saturation, cfg.color_gamma, cfg.color_contrast}, scale);")
edit_if_present("src/app/main.cpp", "gpu.render(cmd, hires, screen_w, H, game->board().video(), 1, pixel_w, pixel_h);", "gpu.render(cmd, hires, screen_w, H, game->board().video(),\n                           {cfg.color_saturation, cfg.color_gamma, cfg.color_contrast}, 1, pixel_w, pixel_h);")
edit_one_or_two("src/app/main.cpp", "gpu.render(cmd, screen, screen_w, H, game->board().video());", "gpu.render(cmd, screen, screen_w, H, game->board().video(),\n                           {cfg.color_saturation, cfg.color_gamma, cfg.color_contrast});")

print("GPU display colour correction added through vertex uniforms")


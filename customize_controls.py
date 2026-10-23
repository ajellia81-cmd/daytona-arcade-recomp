"""Adaptive touch controls and user-configurable menu action."""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else 'source')
def edit(name, old, new, count=1):
    p = root / name
    s = p.read_text()
    assert s.count(old) == count, (name, old, s.count(old))
    p.write_text(s.replace(old, new))

edit('src/app/main.cpp', 'else {} // Controller-only build: no virtual buttons',
     'else if (!devices.pad) app::draw_touch_controls(touch); // Hide only while a gamepad is connected')
edit('src/app/main.cpp', 'in_launcher = e.tfinger.x >= 0.90f && e.tfinger.y <= 0.12f; // Top-right tap opens menu',
     'in_launcher = touch.down(e.tfinger.touchID, e.tfinger.fingerID, tx, ty);')
edit('src/app/main.cpp', 'if (!in_launcher && (e.type == SDL_EVENT_FINGER_DOWN',
     'if (!in_launcher && !devices.pad && (e.type == SDL_EVENT_FINGER_DOWN')
edit('src/app/main.cpp', 'if (in_launcher) touch.clear();', 'if (in_launcher || devices.pad) touch.clear();', 2)
edit('src/app/main.cpp', '    while (running) {', '    bool menu_held = false;\n    while (running) {')
edit('src/app/main.cpp', '            devices.handle_event(e);', '''            devices.handle_event(e);
#ifdef M2_MOBILE
            if (devices.pad) touch.clear();
#endif''')
edit('src/app/main.cpp', '''        // The mouse cursor: hidden while''', '''        const bool menu_down = cfg.controls.value(app::Menu, SDL_GetKeyboardState(nullptr), devices) > 0.5f;
        if (menu_down && !menu_held && !in_launcher) in_launcher = true;
        menu_held = menu_down; // One opening per press; holding cannot reopen after Resume.
        // The mouse cursor: hidden while''')
edit('src/app/controls.h', '    Coin, Start, Test, Service,', '    Coin, Start, Test, Service, Menu,')
edit('src/app/controls.cpp', '{"Service", "service"},', '{"Service", "service"}, {"Open menu", "menu"},')
edit('src/app/controls.cpp', '    b(Service, SDL_SCANCODE_F3, PadInput::None, 0);', '''    b(Service, SDL_SCANCODE_F3, PadInput::None, 0);
    b(Menu, SDL_SCANCODE_ESCAPE, PadInput::Button, SDL_GAMEPAD_BUTTON_RIGHT_STICK);''')
# If the selected pad goes away but another pad remains, keep controls hidden
# and select the remaining pad instead of pretending all pads disconnected.
edit('src/app/controls.cpp', '        if (pad && e.gdevice.which == SDL_GetGamepadID(pad)) SDL_CloseGamepad(pad), pad = nullptr;', '''        if (pad && e.gdevice.which == SDL_GetGamepadID(pad)) {
            SDL_CloseGamepad(pad); pad = nullptr;
            int count = 0;
            SDL_JoystickID *ids = SDL_GetGamepads(&count);
            for (int i = 0; ids && i < count && !pad; ++i)
                if (ids[i] != e.gdevice.which) pad = SDL_OpenGamepad(ids[i]);
            SDL_free(ids);
        }''')
print('Adaptive touch controls restored; Controls > Open menu is bindable (default R3)')


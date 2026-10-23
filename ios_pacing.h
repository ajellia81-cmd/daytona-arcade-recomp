#pragma once
#include <SDL3/SDL.h>
#include <string>
namespace app {
// 0 arcade clock, 1 60 fps sync, 2 experimental native presentation pacing.
void ios_pacing_update(SDL_Window *window, int mode, bool playing);
void ios_pacing_wait();
std::string ios_pacing_status();
void ios_pacing_close();
}

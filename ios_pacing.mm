#import <UIKit/UIKit.h>
#import <QuartzCore/QuartzCore.h>
#include "ios_pacing.h"
#include "app/pacing.h"
#include <algorithm>
#include <cmath>
#include <cstdio>

// A retained presentation handler owns its probe until Metal calls it.
// No callback dereferences a destroyed SDL window or window properties.
@interface DaytonaPacingProbe : NSObject
@property(nonatomic) uint64_t generation;
@property(nonatomic) uint64_t samples;
@property(nonatomic) double previous;
@property(nonatomic) double sum;
@property(nonatomic) double minimum;
@property(nonatomic) double maximum;
@property(nonatomic) double callbackInterval;
- (void)recordTime:(double)time generation:(long long)generation;
- (void)displayTick:(CADisplayLink *)link;
@end
@implementation DaytonaPacingProbe
- (void)recordTime:(double)time generation:(long long)generation {
    @synchronized(self) {
        if ((uint64_t)generation != self.generation || time <= 0) return;
        const double dt = time - self.previous;
        if (self.previous > 0 && dt > 0 && dt < 0.25) {
            self.samples++;
            self.sum += dt;
            self.minimum = std::min(self.minimum, dt);
            self.maximum = std::max(self.maximum, dt);
        }
        self.previous = time;
    }
}
- (void)displayTick:(CADisplayLink *)link {
    @synchronized(self) {
        self.callbackInterval = link.targetTimestamp - link.timestamp;
    }
}
@end

namespace {
DaytonaPacingProbe *probe;
CADisplayLink *displayLink;
SDL_Window *activeWindow;
int activeMode = -1;
bool activePlaying = false, nativeFallback = false;
uint64_t nextTick = 0, changedAt = 0, lastLog = 0;
FILE *logFile;
double requested = 0;
void resetProbe() {
    @synchronized(probe) {
        probe.generation++;
        probe.samples = 0;
        probe.previous = probe.sum = probe.maximum = 0;
        probe.minimum = 1;
    }
    SDL_SetNumberProperty(SDL_GetWindowProperties(activeWindow), "daytona.pacing.generation", probe.generation);
}
}

namespace app {
void ios_pacing_update(SDL_Window *window, int mode, bool playing) {
    if (!probe) {
        activeWindow = window;
        probe = [DaytonaPacingProbe new];
        displayLink = [CADisplayLink displayLinkWithTarget:probe selector:@selector(displayTick:)];
        [displayLink addToRunLoop:NSRunLoop.mainRunLoop forMode:NSRunLoopCommonModes];
        SDL_SetPointerProperty(SDL_GetWindowProperties(window), "daytona.pacing.probe", (__bridge void *)probe);
        const char *documents = SDL_GetUserFolder(SDL_FOLDER_DOCUMENTS);
        if (documents) {
            std::string path = std::string(documents) + "daytona-pacing.csv";
            logFile = std::fopen(path.c_str(), "a");
            if (logFile) std::fprintf(logFile, "session,mode,playing,requested_hz,displaylink_hz,presentation_samples,presentation_mean_ms,min_ms,max_ms,metal_request_fallback,hardware_vrr_verified\n");
        }
    }
    const uint64_t now = SDL_GetTicksNS();
    if (mode != activeMode || playing != activePlaying) {
        activeMode = mode;
        activePlaying = playing;
        nativeFallback = false;
        nextTick = 0;
        changedAt = now;
        resetProbe();
        UIWindow *native = (__bridge UIWindow *)SDL_GetPointerProperty(SDL_GetWindowProperties(window), SDL_PROP_WINDOW_UIKIT_WINDOW_POINTER, nullptr);
        const float maximum = float(native.screen.maximumFramesPerSecond ?: 60);
        requested = mode == 2 && playing ? std::min(double(maximum), kArcadeFrameHz) : maximum;
        // These are preferences, never claims about the panel's real refresh.
        displayLink.preferredFrameRateRange = CAFrameRateRangeMake(float(requested), float(requested), float(requested));
    }
    double mean, minimum, maximum, callback;
    uint64_t samples;
    @synchronized(probe) {
        samples = probe.samples;
        mean = samples ? probe.sum / samples : 0;
        minimum = probe.minimum;
        maximum = probe.maximum;
        callback = probe.callbackInterval;
    }
    // A fixed-refresh panel may quantize a 17.38 ms minimum to 25 or 33 ms.
    // Do not leave the player at that lower rate: remove the Metal hold and
    // retain wall-clock arcade timing, with honest fallback status.
    if (mode == 2 && playing && !nativeFallback && now - changedAt > 3000000000ULL &&
        samples >= 30 && mean > 1.04 / kArcadeFrameHz) {
        nativeFallback = true;
        resetProbe();
        nextTick = 0;
    }
    const double duration = mode == 2 && playing && !nativeFallback ? 1.0 / kArcadeFrameHz : 0;
    SDL_SetFloatProperty(SDL_GetWindowProperties(window), "daytona.pacing.minimum_duration", float(duration));
    if (now - lastLog >= 1000000000ULL) {
        lastLog = now;
        if (logFile) {
            std::fprintf(logFile, "%llu,%d,%d,%.5f,%.3f,%llu,%.4f,%.4f,%.4f,%d,0\n",
                (unsigned long long)(now / 1000000), mode, playing, requested, callback > 0 ? 1 / callback : 0,
                (unsigned long long)samples, mean * 1000, samples ? minimum * 1000 : 0, maximum * 1000, nativeFallback);
            std::fflush(logFile);
        }
    }
}
void ios_pacing_wait() {
    if (activeMode != 2 || !activePlaying || nativeFallback) { nextTick = 0; return; }
    const uint64_t now = SDL_GetTicksNS();
    const uint64_t step = uint64_t(std::llround(1e9 / kArcadeFrameHz));
    if (!nextTick || now > nextTick + step) nextTick = now;
    if (nextTick > now) SDL_DelayPrecise(nextTick - now);
    nextTick += step;
}
std::string ios_pacing_status() {
    if (!probe) return "iOS pacing: waiting for samples";
    double mean, callback;
    uint64_t samples;
    @synchronized(probe) {
        samples = probe.samples;
        mean = samples ? probe.sum / samples : 0;
        callback = probe.callbackInterval;
    }
    char text[512];
    std::snprintf(text, sizeof text,
        "%s; requested %.2f Hz, display-link %.2f Hz; Metal presentations %.2f/s (%llu samples). %s Hardware VRR not verified. Diagnostics: Files > Daytona USA > daytona-pacing.csv",
        activeMode == 1 ? "60 fps sync (+4.3% game speed)" : activeMode == 2 ? "57.52 fps native pacing request" : "57.52 fps arcade clock",
        requested, callback > 0 ? 1 / callback : 0, mean > 0 ? 1 / mean : 0, (unsigned long long)samples,
        nativeFallback ? "Minimum-duration request fell below target; using arcade clock fallback." : "iOS chooses actual refresh.");
    return text;
}
void ios_pacing_close() {
    [displayLink invalidate];
    displayLink = nil;
    if (activeWindow) SDL_ClearProperty(SDL_GetWindowProperties(activeWindow), "daytona.pacing.probe");
    probe = nil; // in-flight Metal blocks retain the old object safely
    if (logFile) std::fclose(logFile);
    logFile = nullptr;
    activeWindow = nullptr;
}
}

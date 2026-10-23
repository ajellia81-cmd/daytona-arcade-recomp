#include "app/pacing.h"
#include <cassert>
#include <cmath>
#include <cstdio>

int main() {
    using namespace app;
    // Misleading reported rates must never drive game speed on iOS.
    for (double hz : {0., 30., 60., 80., 120.}) {
        const Pacing off = choose_pacing(hz, {});
        const Pacing sync = choose_pacing(hz, {false, true, false});
        const Pacing vrr = choose_pacing(hz, {false, false, true});
        const Pacing both = choose_pacing(hz, {false, true, true});
        assert(off.mode == Pacing::Mode::Clock && off.game_hz == kArcadeFrameHz);
        assert(sync.mode == Pacing::Mode::Clock && sync.game_hz == 60.);
        assert(vrr.mode == Pacing::Mode::Clock && vrr.game_hz == kArcadeFrameHz);
        assert(both == vrr); // legacy conflicting settings remain deterministic
        // Simulate 30/60/80/120 presentation loops, including late passes.
        for (int loopHz : {30, 60, 80, 120}) {
            for (const Pacing &p : {off, sync, vrr}) {
                Pacer clock;
                clock.set(p, 0);
                int frames = 0;
                for (int i = 1; i <= loopHz * 60; ++i)
                    frames += clock.frames(uint64_t(std::llround(double(i) * 1e9 / loopHz)));
                assert(std::abs(double(frames) - p.game_hz * 60) <= 1.01);
                clock.pause(60000000000ULL);
                assert(clock.frames(60000000000ULL) == 0);
            }
        }
    }
    std::puts("iOS pacing logic passed: clock/sync/VRR, conflicting settings, varying cadence, pause");
}

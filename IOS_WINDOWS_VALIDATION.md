# Free CI validation results

Workflow run: https://github.com/ajellia81-cmd/daytona-arcade-recomp/actions/runs/39876358996
Source commit: 371c3393a0263b2f328be4d95bd5e538245f18e8

- Shared shaders: SPIR-V, DXIL and MSL generation succeeded.
- iOS: 30/60/80/120 Hz simulated-loop timing tests passed; original desktop pacing tests passed; Xcode arm64 iphoneos daytona_app target built successfully, including ios_pacing.mm and the patched SDL_gpu_metal.m. Log ends BUILD SUCCEEDED.
- Windows: daytona_app target compiled with ClangCL; app_pacing, app_config and app_controls tests all passed (3/3).
- This proves source compilation and automated logic validation, not physical panel, controller, GPU output or gameplay verification.
- Final ROM-dependent IPA/EXE packaging did not run: private-input.enc was not present. Browser file upload was rejected by its upload approval gate. No alternate route was used to bypass that rejection.
- The original private repository remains private. No plaintext ROM, private icon, generated game code, IPA or EXE was published.
- A repository-specific encrypted-input key was registered through the approved Actions Secret flow; no key is stored in this repository.

Remaining: approved encrypted input transfer, ROM code generation, final app link/package checks, encrypted artifact retrieval/decryption, and optional real-device presentation telemetry review. Hardware VRR is not verified.

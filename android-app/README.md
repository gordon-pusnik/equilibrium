# Android Video Poker Trainer

This is the Android trainer app for Equilibrium. It is a real Android Studio project built with Kotlin, Jetpack Compose, JNI, and the shared C++ trainer API from `poker-core/c++`.

## Project Layout

- `app/src/main/java/com/example/videopoker/MainActivity.kt`: Compose UI and trainer flow
- `app/src/main/java/com/example/videopoker/NativeBridge.kt`: JNI declarations
- `app/src/main/cpp/native_bridge.cpp`: JNI bridge into `trainer_api.cpp`
- `app/src/main/cpp/CMakeLists.txt`: native build configuration
- `app/src/main/assets`: bundled ML models and runtime assets

## Open And Run

1. Open `android-app/` in Android Studio.
2. Let Gradle sync.
3. Install or configure the Android SDK, NDK, and CMake if prompted.
4. Run the `app` configuration on an emulator or device.

CLI build verification from this folder:

```bash
GRADLE_USER_HOME=/tmp/gradle-home bash ./gradlew :app:assembleDebug
```

## Current Features

- Variant selector:
  - `Jacks or Better 9/6`
  - `Jacks or Better 8/5`
- Expected RTP display for the selected variant
- Paytable display that updates with the current bet
- Solver-backed `Deal` / `Draw` hand flow
- `Best Hold` toggle
- Manual hold toggling when autohold is off
- Deterministic coaching explanation panel for the solver-recommended hold
- Mistake severity feedback for player-selected holds
- Solver EV details:
  - best EV
  - next-best hold
  - EV edge
- Winning-card highlighting in the final hand

## ML Models

The app no longer asks for a model path in the UI. Variant-specific ML models remain bundled for shared-core evaluation and future product work:

- `jacks_or_better_9_6` -> `app/src/main/assets/modeljob96.json`
- `jacks_or_better_8_5` -> `app/src/main/assets/modeljob85.json`

The current trainer UI does not expose ML mode or engine switching.

## Native Bridge Surface

The Android bridge uses the shared trainer API to:

- create and destroy a native trainer handle
- set variant
- set engine for internal/native configuration
- load an ML model for shared-core support
- deal a hand with a suggested hold mask
- draw with a supplied hold mask
- request hold explanations
- request solver EV comparison data
- analyze player holds against solver-best play for coaching feedback

## Notes

- The Android UI is top-pinned so the layout stays stable when the final hand appears or disappears.
- The current Android trainer experience is solver-backed.
- Rule and ML engine support still exists in the shared core and CLI tools, but it is not exposed in the current trainer UI.

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
- Engine selector for solver, rule, and ML/AI mode
- `Deal` / `Draw` hand flow
- `Autohold` toggle
- Manual hold toggling when autohold is off
- Switch engines after dealing to compare recommended holds on the same hand
- Explanation panel for why the recommended hold was chosen
- Solver-only EV details:
  - best EV
  - next-best hold
  - EV edge
- Winning-card highlighting in the final hand

## ML Models

The app no longer asks for a model path in the UI. In ML mode it uses a bundled model based on the selected variant:

- `jacks_or_better_9_6` -> `app/src/main/assets/modeljob96.json`
- `jacks_or_better_8_5` -> `app/src/main/assets/modeljob85.json`

## Native Bridge Surface

The Android bridge uses the shared trainer API to:

- create and destroy a native trainer handle
- set engine
- set variant
- load an ML model
- deal a hand with a suggested hold mask
- draw with a supplied hold mask
- recalculate suggested holds for an already-dealt hand
- request hold explanations
- request solver EV comparison data

## Notes

- The Android UI is top-pinned so the layout stays stable when the final hand appears or disappears.
- The rule and solver engines are the stronger strategy references today. The ML engine is present for comparison and experimentation.

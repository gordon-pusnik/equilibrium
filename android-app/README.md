# Android Video Poker Trainer (Kotlin + Compose + JNI)

This folder contains an Android Studio project scaffold that renders a video-poker style trainer UI and calls the C++ engine through JNI.

## Structure

- `app/src/main/java/com/example/videopoker/MainActivity.kt`: Compose UI
- `app/src/main/java/com/example/videopoker/NativeBridge.kt`: JNI declarations
- `app/src/main/cpp/native_bridge.cpp`: JNI -> C++ trainer API bridge
- `app/src/main/cpp/CMakeLists.txt`: builds native shared library with core C++ engine

## Open and Run

1. Open `android-app/` in Android Studio.
2. Let Gradle sync and install NDK/CMake when prompted.
3. Build and run on emulator/device.

## Engine Integration

Native layer calls `poker-core/c++/trainer_api.cpp` and exposes:

- create/destroy context
- set engine (`solver`, `rule`, `ml`)
- load ML model JSON path
- play one hand and return card/payout data

## UI Features Included

- Engine selector: `solver`, `rule`, `ml`
- Bet controls (`1...5`)
- Autohold toggle
- ML model path input for `ml`
- `Deal Hand`: deals a hand (optionally with automatic holds)
- Tap initial cards to manually toggle holds
- `Draw Selected`: draws using user hold selection
- Final hand display with winning cards highlighted
- Payout display

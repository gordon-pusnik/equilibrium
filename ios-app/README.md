# iOS Video Poker Trainer

This is the iOS trainer app for Equilibrium. It is a working Xcode project built with SwiftUI and an Objective-C++ bridge into the shared C++ trainer API in `poker-core/c++`.

## Project Layout

- `VideoPokerTrainer.xcodeproj`: Xcode project
- `VideoPokerTrainer/App`: SwiftUI screens and app flow
- `VideoPokerTrainer/Engine`: Objective-C++ bridge files
- `VideoPokerTrainer/Resources`: card images, plist, bridging header, bundled ML models

## Open And Run

1. Open `ios-app/VideoPokerTrainer.xcodeproj` in Xcode.
2. Select the `VideoPokerTrainer` scheme.
3. Set your Apple signing team if you want to run on a physical device.
4. Build and run on a simulator or device.

Command-line build verification example:

```bash
/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild \
  -project ios-app/VideoPokerTrainer.xcodeproj \
  -scheme VideoPokerTrainer \
  -configuration Debug \
  -destination 'generic/platform=iOS' \
  -derivedDataPath /tmp/vpt-derived-data \
  CODE_SIGNING_ALLOWED=NO \
  build
```

## Current Features

- Game picker:
  - `Jacks or Better 9/6`
  - `Jacks or Better 8/5`
- Expected RTP display for the selected variant
- Paytable display that updates with the current bet
- Solver-backed `Deal` / `Draw` hand flow
- `Best Hold` toggle
- Manual hold selection when autohold is off
- Expandable deterministic coaching explanation panel for the recommended hold
- Mistake severity feedback for player-selected holds
- Solver EV detail rows for best EV, next-best hold, and EV edge
- Winning-card highlighting in the final hand

## ML Models

The app no longer exposes a model-path field. Variant-specific ML models remain bundled for shared-core evaluation and future product work:

- `jacks_or_better_9_6` -> `VideoPokerTrainer/Resources/modeljob96.json`
- `jacks_or_better_8_5` -> `VideoPokerTrainer/Resources/modeljob85.json`

The current trainer UI does not expose ML mode or engine switching.

## Bridge Responsibilities

The Objective-C++ bridge exposes the shared trainer API to SwiftUI for:

- handle creation and destruction
- variant selection
- engine selection for internal/native configuration
- ML model loading for shared-core support
- deal and draw operations
- hold explanation lookup
- solver EV comparison analysis
- player-hold mistake analysis for coaching feedback

## Notes

- The iOS app uses the same native strategy logic as Android and the CLI tools.
- The current iOS trainer experience is solver-backed.
- Rule and ML engine support still exists in the shared core and CLI tools, but it is not exposed in the current trainer UI.

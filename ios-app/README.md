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
- Engine picker for solver, rule, and ML
- `Deal` / `Draw` hand flow
- `Autohold` toggle
- Manual hold selection when autohold is off
- Switch engines after dealing to compare recommended holds on the same hand
- Expandable explanation panel for the recommended hold
- Solver-only EV detail rows for best EV, next-best hold, and EV edge
- Winning-card highlighting in the final hand

## ML Models

The app no longer exposes a model-path field. In ML mode it loads a bundled model based on the selected variant:

- `jacks_or_better_9_6` -> `VideoPokerTrainer/Resources/modeljob96.json`
- `jacks_or_better_8_5` -> `VideoPokerTrainer/Resources/modeljob85.json`

## Bridge Responsibilities

The Objective-C++ bridge exposes the shared trainer API to SwiftUI for:

- handle creation and destruction
- engine selection
- variant selection
- ML model loading
- deal and draw operations
- hold recalculation for an already-dealt hand
- hold explanation lookup
- solver EV comparison analysis

## Notes

- The iOS app uses the same native strategy logic as Android and the CLI tools.
- The ML engine is currently useful for side-by-side comparison, but the rule and solver engines remain the stronger references.

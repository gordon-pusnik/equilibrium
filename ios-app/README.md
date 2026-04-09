# iOS Video Poker Trainer (SwiftUI + Objective-C++)

This folder contains a starter iOS app scaffold that uses the C++ poker engine through an Objective-C++ bridge.

## Structure

- `VideoPokerTrainer/App/`: SwiftUI app UI
- `VideoPokerTrainer/Engine/`: Objective-C++ bridge (`PokerEngineBridge.mm`) calling `poker-core/c++/trainer_api.*`
- `VideoPokerTrainer/Resources/VideoPokerTrainer-Bridging-Header.h`: Swift bridging header

## What You Need To Do In Xcode

1. Create a new **iOS App** project named `VideoPokerTrainer` (SwiftUI + Swift).
2. Replace generated Swift files with files from `ios/VideoPokerTrainer/App/`.
3. Add `PokerEngineBridge.h/.mm` to the Xcode project.
4. Add C++ engine sources to the target build:
   - `poker-core/c++/card.cpp`, `poker-core/c++/deck.cpp`, `poker-core/c++/hand.cpp`, `poker-core/c++/checkforwin.cpp`, `poker-core/c++/autohold.cpp`, `poker-core/c++/trainer_api.cpp`, `poker-core/c++/evaluator.cpp`
5. Add headers to Header Search Paths (recursive):
   - `$(PROJECT_DIR)/../../poker-core/c++`
6. Set Objective-C Bridging Header to:
   - `VideoPokerTrainer/Resources/VideoPokerTrainer-Bridging-Header.h`
7. Ensure source files with C++ calls are compiled as Objective-C++ (`.mm`).

## UI Features Included

- Engine selector: `solver`, `rule`, `ml`
- Bet selector (`1...5`)
- ML model path field (shown when `ml` selected)
- `Deal`: deals a hand and allows manual selection (unless Autohold is ON)
- Tap initial cards to manually toggle held state
- `Draw`: draws using user-selected hold mask
- Graphical card row for final hand with winning cards highlighted
- Payout display

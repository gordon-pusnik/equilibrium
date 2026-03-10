# Video Poker Suite (C++, Python, Mobile, API)

A high-performance, multi-platform Jacks-or-Better video poker suite. This project features a modernized C++17 core engine, an exhaustive EV-optimal solver, machine learning integration, and a full suite of applications including CLI tools, mobile trainers, and a dockerized REST API.

## 🚀 Key Features

### High-Performance Core (`poker-core/c++`)
- **Modernized C++17:** Uses smart pointers (`std::unique_ptr`), standard containers (`std::array`, `std::vector`), and thread-local caching for memory safety and speed.
- **Bitmask Evaluation:** Hand evaluation uses bitwise operations for constant-time detection of straights, flushes, and rank frequencies.
- **Exhaustive Solver:** Guaranteed EV-maximizing play by simulating all 32 hold combinations against all remaining deck permutations.
- **Multi-threaded Simulation:** CLI tools leverage all available CPU cores for massive throughput during data generation and RTP verification.

### Machine Learning Engine
- **Tiny MLP:** Efficient feed-forward neural network implementation in both C++ and Python.
- **Training Pipeline:** Generate millions of rows of solver-perfect training data and train a custom strategy policy in minutes.

### Mobile Trainer Apps (`android-app`, `ios-app`)
- **Cross-Platform Logic:** Shares the exact same C++ core via JNI (Android) and Objective-C++ (iOS).
- **Interactive UI:** Centered layout with graphical card assets and professional animations.
- **Real-time Feedback:** Highlights winning cards in the final hand and provides "HELD" status badges.
- **Manual Mode:** Toggle "Autohold" off to play manually and compare your choices against the optimal engine strategy.
- **Dynamic Seeding:** Real-time randomization ensures a unique deck every time the app is launched.

### API Microservice (`api-server`)
- **FastAPI Powered:** A modern, high-performance Python API server.
- **Optimal Play Endpoint:** Submit a hand and receive the exact hold mask and Expected Value (EV).
- **Dockerized:** Fully containerized for easy deployment as a microservice.

---

## 📂 Repository Structure

- `poker-core/`
  - `c++/`: Core logic, Evaluators, Solver, and Trainer API.
  - `python/`: ML Training scripts and Python versions of the engine.
- `android-app/`: Kotlin + Jetpack Compose Android application.
- `ios-app/`: Swift + SwiftUI iOS application.
- `api-server/`: FastAPI server and Docker configuration.
- `resources/`: Graphical assets (cards, UI).

---

## 🛠 Building & Setup

### C++ CLI Tools
Build high-performance binaries from the root directory:

```bash
# Build Gameplay Simulator
g++ -std=c++17 -O3 poker-core/c++/main.cpp poker-core/c++/deck.cpp poker-core/c++/hand.cpp poker-core/c++/card.cpp poker-core/c++/checkforwin.cpp poker-core/c++/autohold.cpp poker-core/c++/evaluator.cpp -o videopoker -lpthread

# Build RTP Verifier
g++ -std=c++17 -O3 poker-core/c++/verify_rtp.cpp poker-core/c++/autohold.cpp poker-core/c++/checkforwin.cpp poker-core/c++/card.cpp poker-core/c++/evaluator.cpp -o verify_rtp -lpthread
```

### API Server (Docker)
Build and run the REST API:

```bash
docker build -t videopoker-api -f api-server/Dockerfile .
docker run -p 8000:8000 videopoker-api
```

---

## 🎮 Usage Examples

### CLI Gameplay
Run a simulation session with the optimal solver:
```bash
./videopoker 100 1 10  # [starting_coins] [bet] [iterations]
```

### RTP Verification
Verify the Return to Player percentage over millions of hands:
```bash
./verify_rtp --engine solver 10000 20 5 12345 # [hands_per_run] [runs] [bet] [seed]
```

### API Optimal Play
Query the solver for a specific hand:

#### Usage Example

```bash
curl -X POST http://localhost:8000/v1/video-poker/strategy \
  -H "Content-Type: application/json" \
  -d '{
    "variant": "jacks_or_better", 
    "hand": ["Ah", "Kh", "Qh", "Jh", "2c"], 
    "bet": 5,
    "engine": "solver"
  }'
```

Response:
```json
{
  "hold": ["Ah", "Kh", "Qh", "Jh"],
  "ev": 1.21,
  "ev_per_coin": 0.242
}
```

### API Hand Evaluation
Get the exact rank and name of any 5-card hand (1 = Best, 7462 = Worst).

#### Usage Example

```bash
curl -X POST http://localhost:8000/v1/poker/evaluate \
  -H "Content-Type: application/json" \
  -d '{"hand": ["Ah", "Kh", "Qh", "Jh", "10h"]}'
```

Response:
```json
{
  "hand_name": "Royal Flush",
  "rank_value": 1
}
```


### ML Data Generation & Training
1. **Generate Data:** `./videopoker --engine solver --dump-training training.jsonl 1000000 1 100000`
2. **Train Model:** `python3 poker-core/python/train_ml_engine.py training.jsonl model.json`
3. **Use Model:** `./videopoker --engine ml --ml-model model.json 100 1 50`

---

## 📱 Mobile Features

The mobile applications in `android-app/` and `ios-app/` provide a rich training experience:
- **Winning Card Highlights:** Cards part of a winning payout are highlighted with a yellow border and a "WIN" badge.
- **HELD Badges:** Cards selected for hold are marked at the bottom, matching the win text style.
- **Trainer Mode:** When Autohold is ON, the app automatically holds the EV-optimal cards. When OFF, you choose manually, and the app uses Red/Green borders to show if your choices were correct.
- **Extensible:** The core is designed to support future paytables (Deuces Wild, Bonus Poker) by simply adding new evaluation logic to `payout_for_cards`.

---

## 📄 License
This project is for educational and simulation purposes. Check individual platform READMEs for specific build requirements (Android Studio / Xcode).

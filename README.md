# Equilibrium

![C++](https://img.shields.io/badge/C%2B%2B-17-blue)
![Python](https://img.shields.io/badge/Python-3.x-yellow)
![FastAPI](https://img.shields.io/badge/API-FastAPI-green)
![Docker](https://img.shields.io/badge/Container-Docker-blue)
![iOS](https://img.shields.io/badge/iOS-SwiftUI-black)
![Android](https://img.shields.io/badge/Android-Kotlin-brightgreen)
![Solver](https://img.shields.io/badge/Strategy-EV%20Solver-orange)
![ML](https://img.shields.io/badge/MachineLearning-MLP-purple)

A high-performance, multi-platform training suite built on **Equilibrium**, a C++ strategy solver designed to compute mathematically optimal play using exhaustive expected value analysis and simulation.

The project includes:

* a high-performance C++ engine
* machine learning strategy models
* mobile trainer applications
* a Dockerized REST API
* command-line simulation tools

The system is capable of evaluating millions of game states to determine optimal decisions.

---

# Overview

This project provides a complete ecosystem for **poker strategy analysis and training**.

The core engine performs exhaustive analysis of every possible hold decision to determine the **expected value maximizing strategy** for a given hand.

Applications built on top of the engine include:

* mobile trainer apps
* command-line simulators
* machine learning training pipelines
* REST API microservices

---

# Key Features

## High-Performance Core Engine (C++)

The Equilibrium engine provides extremely fast card evaluation and strategy computation.

Features include:

* Modern **C++17 implementation**
* Memory-safe architecture using `std::unique_ptr`
* Standard containers (`std::vector`, `std::array`)
* Thread-local caching for performance
* Bitmask-based hand evaluation
* Multi-threaded simulation tools

### Bitmask Hand Evaluation

Hand evaluation uses optimized **bitwise operations** for fast detection of:

* straights
* flushes
* rank frequencies

This enables constant-time evaluation for most operations.

---

## Exhaustive Optimal Solver

The strategy engine computes the **true optimal play** for each hand.

For every deal:

* All **32 possible hold combinations** are tested
* Each hold is simulated against **all remaining deck permutations**
* Expected value (EV) is computed
* The EV-maximizing strategy is selected

This guarantees mathematically optimal play.

---

## Multi-Threaded Simulation

Simulation tools utilize all available CPU cores.

Used for:

* RTP verification
* EV analysis
* large-scale training data generation

This allows millions of hands to be simulated quickly.

---

# Machine Learning Strategy Engine

The system includes a lightweight machine learning pipeline.

Features include:

* Tiny **MLP neural network**
* Implementations in **C++ and Python**
* Fast training pipeline
* Solver-generated training datasets

Training workflow:

1. Generate solver-perfect training data
2. Train neural network model
3. Use model for extremely fast approximate strategy decisions

This allows experimentation with **ML-based strategy engines**.

---

# Mobile Trainer Applications

The project includes full mobile applications for both major platforms.

## Android App

* Kotlin
* Jetpack Compose UI
* JNI integration with the C++ engine

## iOS App

* Swift
* SwiftUI interface
* Objective-C++ bridge to the C++ core

Both mobile apps use the **same C++ strategy engine**, ensuring identical optimal decisions.

---

# Mobile Trainer Features

The mobile trainers provide an interactive learning environment.

Features include:

### Real-Time Strategy Feedback

When playing manually, the app evaluates your decisions against the optimal solver.

* correct holds highlighted in **green**
* incorrect holds highlighted in **red**

### Autohold Mode

Automatically holds EV-optimal cards for each hand.

Useful for learning correct strategy patterns.

### Winning Hand Highlights

Cards contributing to a winning payout are displayed with:

* yellow borders
* "WIN" badge indicators

### Held Card Indicators

Cards selected for hold display a **HELD badge**.

### Dynamic Random Seeding

Each application launch generates a new randomized deck ensuring varied gameplay.

---

# REST API Microservice

The engine can be accessed via a REST API implemented with:

* **FastAPI**
* **Uvicorn**

The API is fully **Dockerized** for easy deployment.

---

## Optimal Strategy Endpoint

Submit a hand and receive the optimal hold decision.

Example request:

```bash
POST /v1/video-poker/strategy
```

Example payload:

```json
{
  "variant": "jacks_or_better",
  "hand": ["Ah","Kh","Qh","Jh","2c"],
  "bet": 5,
  "engine": "solver"
}
```

Example response:

```json
{
  "hold": ["Ah","Kh","Qh","Jh"],
  "ev": 1.21,
  "ev_per_coin": 0.242
}
```

---

## Hand Evaluation Endpoint

Evaluate any five-card poker hand.

Example request:

```bash
POST /v1/poker/evaluate
```

Payload:

```json
{
  "hand": ["Ah","Kh","Qh","Jh","10h"]
}
```

Response:

```json
{
  "hand_name": "Royal Flush",
  "rank_value": 1
}
```

Ranking system:

* **1 = Best possible hand**
* **7462 = Worst possible hand**

---

# Command-Line Simulation Tools

High-performance CLI tools are included for research and validation.

## Gameplay Simulation

```bash
./videopoker 100 1 10
```

Parameters:

```
[starting_coins] [bet] [iterations]
```

---

## RTP Verification

Verify theoretical return-to-player percentages.

```bash
./verify_rtp --engine solver 10000 20 5 12345
```

Parameters:

```
[hands_per_run] [runs] [bet] [seed]
```

---

# Machine Learning Training Pipeline

Training data can be generated directly from the solver.

Generate dataset:

```bash
./videopoker --engine solver --dump-training training.jsonl 1000000 1 100000
```

Train model:

```bash
python3 poker-core/python/train_ml_engine.py training.jsonl model.json
```

Run engine with ML strategy:

```bash
./videopoker --engine ml --ml-model model.json 100 1 50
```

---

# Repository Structure

```
poker-core/
  c++/       Core engine, solver, evaluators
  python/    ML training pipeline

android-app/  Android trainer application
ios-app/      iOS trainer application
api-server/   FastAPI microservice
resources/    Graphical assets
```

---

# Extensibility

The system is designed to support additional video poker variants by extending the payout logic.

Planned future variants include:

* Deuces Wild
* Bonus Poker
* Double Bonus Poker

The architecture also allows expansion into other card games.

---

System Architecture

The Trainer ecosystem is powered by the Equilibrium strategy engine, which can be accessed through multiple interfaces including mobile applications, command-line tools, and a REST API.

flowchart TD

A[Equilibrium C++ Engine]

B[Strategy Solver]
C[Hand Evaluator]
D[Monte Carlo Simulation]
E[ML Strategy Engine]

A --> B
A --> C
A --> D
A --> E

F[FastAPI Service]
G[CLI Tools]
H[iOS Trainer App]
I[Android Trainer App]

B --> F
C --> F
D --> G
E --> G

F --> H
F --> I

The Equilibrium engine provides the core functionality used by:

mobile trainer applications

command-line simulation tools

REST API microservices

machine learning training pipelines

# License

© 2026 Gordon Pusnik. All rights reserved.

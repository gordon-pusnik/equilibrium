# Equilibrium Verification Guide

## Purpose

This document defines the preferred verification approach for Equilibrium changes.

Goals:
- prove behavior with the smallest useful check first
- keep validation proportional to the risk of the change
- make it clear what was actually verified
- avoid claiming confidence that was not earned

General rule:
- narrow change -> narrow verification
- core strategy change -> direct strategy and EV validation
- cross-platform change -> validate each affected surface

---

## Verification principles

1. Start small
2. Validate the layer you changed
3. Validate downstream consumers if contracts changed
4. Be explicit when something could not be run
5. Never claim tests ran if they did not

---

## Build baseline

Primary repo build:
```bash
bash ./build.sh
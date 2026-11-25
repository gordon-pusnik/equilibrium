# Milestones

## Milestone 1: Create leakage-resistant dataset splits

**Status: Completed**

### Acceptance criteria

- Group suit-renamed and card-reordered equivalents before partitioning. Verify that no canonical hand appears in more than one split.
- Record split hashes, generation settings, seeds, and paytable versions. Reserve the final test set before retraining.

## Milestone 2: Retrain one model and measure EV loss

**Status: Completed**

### Acceptance criteria

- Compare one retrained model and the current baseline against the exact solver on the same final holdout.
- Report mean expected value (EV) lost, costly outliers, and error slices by hand category and paytable.
- Keep the experiment offline and retain the solver as the source of truth for MVP autohold.

## Milestone 3: Improve the retrained model to outperform the shipped model

**Status: Open**

The retrained model lost 8.11 percentage points of expected return versus 6.38 for the shipped model, a paired difference of 1.73 percentage points in favor of the shipped model.

### Acceptance criteria

- On a fresh, leakage-resistant holdout reserved before tuning, compare the improved model and the shipped model on the same hands against the exact solver. The improved model must have lower mean EV loss than the shipped model.
- Report the paired difference, costly outliers, and EV loss by hand category and paytable.
- Keep the work offline and retain the exact solver as the source of truth for MVP autohold.

**Extended goal:** Minimize the remaining EV loss so the improved model's expected return to player (RTP) comes as close as possible to the exact solver's RTP for each paytable.
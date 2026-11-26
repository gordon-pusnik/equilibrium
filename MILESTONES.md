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

**Status: Completed**

The retrained model lost 8.11 percentage points of expected return versus 6.38 for the shipped model, a paired difference of 1.73 percentage points in favor of the shipped model.

### Acceptance criteria

- On a fresh, leakage-resistant holdout reserved before tuning, compare the improved model and the shipped model on the same hands against the exact solver. The improved model must have lower mean EV loss than the shipped model.
- Report the paired difference, costly outliers, and EV loss by hand category and paytable.
- Keep the work offline and retain the exact solver as the source of truth for MVP autohold.

**Extended goal:** Minimize the standalone trained model's EV loss for each paytable. Exact parity is not a requirement; solver-backed inference corrections do not count toward model improvements.

### 9/6 whole-mask pilot

At five credits, the whole-mask ranker lost **0.079 percentage points** versus the exact solver, compared with **4.726** for the shipped model and **6.452** for the previous retrain. All three used the same zero-payout hold-all guard. The paired improvement over the shipped model was **4.647 points** (approximate 95% interval: **3.951–5.343**).

The 12,000-deal holdout was reserved before training and excludes canonical equivalents from earlier evaluation cohorts. It measures performance on that conditional sample, not full-deck RTP. The ranker made EV-optimal holds on **98.75%** of those deals; the costliest remaining misses broke made straights. This pilot did not establish exact solver parity or evaluate 8/5. MVP autohold remains unchanged.

Local experiment artifacts: `build/whole-mask-job96/` (`plan.json`, `selection.json`, `results.json`).

### 8/5 replication and made-straight correction

On a new shared 16,000-deal holdout at five credits, the whole-mask ranker beat the shipped model on both paytables under the same zero-payout hold-all guard. The holdout excludes prior evaluation groups and the 9/6 pilot's train and validation groups, so these are conditional-sample gaps rather than full-deck RTP estimates.

| Paytable | Shipped loss | Ranker loss | Ranker + exact straight correction loss | Paired ranker improvement over shipped (approx. 95% CI) |
| --- | ---: | ---: | ---: | ---: |
| 9/6 | 4.007 pp | 0.044 pp | 0.022 pp | 3.964 pp (3.605–4.322) |
| 8/5 | 3.622 pp | 0.080 pp | 0.024 pp | 3.542 pp (3.151–3.933) |

For made straights, the correction compares standing pat with any four-card royal draw. It matched exact solver EV on all **500 canonical made-straight classes** for each paytable, including the six classes where breaking for a royal is optimal. It eliminated all straight losses in the main holdout and the separate 153-class stress cohort. The costliest remaining holdout misses were high-card draw decisions. The correction is offline only; MVP autohold remains solver-authoritative, and exact parity for all hands is not established.

Local experiment artifacts: `build/whole-mask-followup/` (`plan.json`, `selection.json`, `results.json`, and `followup.py`).

### Standalone model improvement plan

Compare models without guards or solver calls at inference. Select checkpoints on validation mean EV loss and reserve a fresh holdout by canonical hand group before tuning. Track costly mistakes, made straights, and high-card decisions where holding four cards competes with holding zero or two.

1. **Target the training data.** Add solver-labeled made straights, including exceptions where breaking for a royal is correct, and high-card hands with competing four-card draws. Keep ordinary examples in the mix. Compare targeted and random additions of the same size, with architecture and loss held fixed.
2. **Penalize costly ranking mistakes directly.** Add a loss that pushes an EV-optimal hold above the model's highest-scoring wrong hold in proportion to the EV gap, while treating equal-EV actions as ties. Compare the loss change alone and in combination with targeted data.
3. **Improve draw features if needed.** Give the model the rank–suit relationships of held cards and the blockers among discarded cards before increasing network size.

#### Experiment 1: Targeted training data

Both arms used the same 55,000 canonical base groups and added 6,500 groups: randomly for the control, or enriched for made straights and competing four-card draws for the targeted arm. Architecture, loss, training budget, and seeds were held fixed. Checkpoints were selected on 6,000 validation groups. Both arms were then scored with no guard or solver correction on a fresh shared 18,000-deal holdout (16,302 canonical classes), excluding previously evaluated groups.

| Paytable | Random additions: EV loss | Targeted additions: EV loss | Paired improvement (approx. 95% CI) |
| --- | ---: | ---: | ---: |
| 9/6 | 0.1227 pp | 0.0419 pp | 0.0809 pp (0.0064–0.1553) |
| 8/5 | 0.0419 pp | 0.0308 pp | 0.0111 pp (0.0063–0.0159) |

On 9/6, made-straight errors fell from five to one. On 8/5, the same straight error remained, and four-versus-zero/two high-card mistakes increased from 39 to 62 despite lower overall EV loss. Each targeted model still made a costly straight error, and neither training arm contained an eligible made-straight royal exception. Retain targeted data as a promising input to the costly-ranking-loss experiment, not as evidence that the problem is solved. The holdout results are conditional on the excluded groups, not full-deck RTP estimates.

Local experiment artifacts: `build/whole-mask-targeted/` (`plan.json`, `results.json`, and `targeted.py`).

#### Experiment 2: Costly-ranking loss

Compared four recipes on each paytable: random or targeted data, each with the original loss or the original loss plus a pairwise ranking penalty. The penalty compared the highest-scoring wrong hold with the highest-scoring EV-optimal hold, weighted by the wrong hold's EV gap (capped at four times the stake). All arms included the six made-straight royal exceptions in the common training base. Checkpoints were selected on unguarded validation EV; the fresh 20,000-deal holdout and 48-class straight stress set were scored only after selection.

| Paytable | Random + original | Random + ranking | Targeted + original | Targeted + ranking |
| --- | ---: | ---: | ---: | ---: |
| 9/6 | 0.0637 pp | 0.0798 pp | **0.0500 pp** | 0.0685 pp |
| 8/5 | 0.0659 pp | 0.0719 pp | **0.0554 pp** | 0.0704 pp |

The tested ranking penalty increased mean holdout EV loss in all four matched comparisons. With targeted data, the 9/6 ranking arm made one fewer straight error but doubled the number of mistakes costing over one credit (5 to 10). Targeted data with the original loss was best on both paytables. Keep that recipe as the control for the draw-feature experiment; these results do not rule out other ranking objectives or weights.

Local experiment artifacts: `build/whole-mask-ranking/` (`plan.json`, `results.json`, and `ranking.py`).

#### Experiment 3: Draw and blocker features

Added 44 card-derived inputs for suited ranks, discard blockers, one-card outs, and dealt straight patterns. The control zeroed those inputs. Both arms used the same parameter count, targeted data, original loss, and seeds. Checkpoints were selected on validation and scored unguarded on a fresh 24,000-deal holdout (18,590 canonical classes), conditional on excluding prior evaluation and selection groups.

| Paytable | Control EV loss | Draw-feature EV loss | Paired improvement (approx. 95% CI) |
| --- | ---: | ---: | ---: |
| 9/6 | 0.03684 pp | **0.01469 pp** | 0.02215 pp (0.00568–0.03861) |
| 8/5 | 0.03225 pp | **0.00419 pp** | 0.02806 pp (0.01057–0.04554) |

The new rankers chose EV-optimal holds for all six made straights in the main holdout and all 12 fresh stress classes on both paytables. Holding four when zero or two was optimal dropped from 59 to 14 on 9/6 and from 60 to three on 8/5. The most expensive remaining decisions were high pairs competing with four to a straight flush; those outliers accounted for roughly 70% of the remaining sample EV loss on each paytable. These are standalone model results, not estimates of full-deck RTP. MVP autohold is unchanged.

Local experiment artifacts: `build/whole-mask-draw-features/` (`plan.json`, `results.json`, `draw_features.py`, and `evaluate.py`).

#### Experiment 4: High-pair conflict replay

Both arms used the original loss, draw features, and the same 61,500 canonical training groups, including all 26 eligible examples of a high pair competing with four to a straight flush. Each arm added 384 training rows per epoch. The control replayed random training hands; the targeted arm split its replay budget between those conflicts and look-alike four-flush hands where keeping the pair was optimal.

| Paytable | Random replay: EV loss | Conflict replay: EV loss | Paired improvement from conflict replay (approx. 95% CI) |
| --- | ---: | ---: | ---: |
| 9/6 | **0.00440 pp** | 0.00446 pp | −0.00006 pp (−0.00139–0.00127) |
| 8/5 | **0.00192 pp** | 0.00289 pp | −0.00097 pp (−0.00199–0.00004) |

Both arms matched solver EV on all 12 fresh conflict classes and all 96 look-alike classes on each paytable. There was no benefit from targeted replay over shared coverage on those stress sets; this comparison did not isolate the effect of including the 26 training conflicts. The 24,000-deal general holdout, which excluded the conflict slice and prior evaluation groups, showed no clear improvement with extra replay. Neither arm lost a full credit on any general holdout deal. Keep the draw features, original loss, and training coverage without giving these conflicts extra replay weight.

Local experiment artifacts: `build/whole-mask-high-pair/` (`plan.json`, `results.json`, and `high_pair.py`).

#### Experiment 5: Learned high-card top-two reranker

Froze the previous experiment’s control checkpoints and verified that they reproduced all 24,000 prior decisions per paytable. A separate learned reranker predicted the signed EV difference between the top two holds from their features and base scores. Training predictions came from three out-of-fold shadow rankers per paytable. Checkpoint and flip thresholds were chosen on the reused validation partition, with no access to the new holdout. No solver or EV labels were used at inference.

| Paytable | Frozen EV loss | Reranked EV loss | High-card misses | Fixed / new errors (deals) |
| --- | ---: | ---: | ---: | ---: |
| 9/6 | 0.006150 pp | **0.004978 pp** | 68 → 48 | 20 / 0 |
| 8/5 | 0.003732 pp | **0.000606 pp** | 55 → 26 | 40 / 11 |

The 24,000 sampled deals covered 2,083 of the 2,089 eligible canonical classes remaining after excluding earlier evaluations, validation groups, and both frozen models’ training groups. The apparent gains came from two corrected classes per paytable, with one class regressing on 8/5. This is encouraging on the reserved cohort but does not establish broad generalization or full-deck RTP. Keep the reranker experimental; for stronger evidence, use a predeclared outer grouped cross-validation protocol that evaluates the entire training and selection pipeline out of fold and weights classes by their deal frequency. MVP autohold is unchanged.

Local experiment artifacts: `build/whole-mask-rerank/` (`plan.json`, `results.json`, and `rerank.py`).

#### Experiment 6: Deal-weighted nested cross-validation

At five credits, evaluated the base and top-two reranking recipes over five outer folds spanning all 134,459 canonical hand classes, weighted by the 2,598,960 unordered deals they represent. Each class was scored only by models that excluded it from training, targeted sampling, and validation. Three inner shadow folds generated the reranker's training pairs. Standalone scoring used no solver, hand EV, or guard at inference.

| Paytable | Base EV loss | Reranked EV loss | Reduction | Outer folds improved |
| --- | ---: | ---: | ---: | ---: |
| 9/6 | 0.002052 pp | **0.000955 pp** | 53.5% | 5/5 |
| 8/5 | 0.002430 pp | **0.001638 pp** | 32.6% | 4/5 |

The reranker corrected 188 canonical classes and introduced 20 errors on 9/6; on 8/5 it corrected 157 and introduced 78. The pooled EV improvement remained positive after omitting any one outer fold. These results measure the retraining and selection recipe, not a single frozen checkpoint; earlier experiments informed the recipe, so this is not a blind external evaluation. Retain the reranker as the experimental training recipe, with a stricter look at harmful flips on 8/5. MVP autohold remains solver-authoritative.

Local experiment artifacts: `build/whole-mask-grouped-cv/` (`plan.json`, `results.json`, `grouped_cv.py`, and per-fold checkpoints).

#### Experiment 7: Conservative 8/5 reranker flips

In the previous folds, vetoing switches from holding three cards to holding zero or one would have prevented 24 harmful flips while suppressing three beneficial flips. Locked that rule and tested it on 8/5 with five different grouped folds, retraining the full base and reranker pipelines. The same canonical universe was reused; this is a split-sensitivity replication, not an external holdout.

| Policy | Deal-weighted EV loss | Canonical errors fixed vs. base | Canonical errors introduced vs. base |
| --- | ---: | ---: | ---: |
| Base ranker | 0.00195826 pp | — | — |
| Ordinary reranker | **0.00119762 pp** | 100 | 34 |
| Reranker with veto | 0.00119812 pp | 98 | 31 |

The veto prevented three harmful class flips but also blocked two beneficial ones and slightly worsened net EV. The ordinary reranker still improved overall EV in all five folds. Keep the ordinary reranker rather than hard-coding the hold-count veto. If harmful flips remain a priority, test agreement across independently trained rerankers or an uncertainty-aware EV estimate, using deal-weighted EV—not just the count of harmful flips—as the primary metric.

Local experiment artifacts: `build/whole-mask-85-flips/` (`protocol.json`, `results.json`, and `conservative.py`).

#### Experiment 8: Agreement between learned rerankers

With base rankers and ordinary rerankers frozen, trained two more rerankers per fold from separate seeds on the same out-of-fold training pairs. Each member selected its flip thresholds on validation. Compared single, majority, and unanimous policies on the existing five outer folds per paytable, weighted by deal frequency.

| Paytable | One reranker: EV loss | Majority: EV loss | Unanimous: EV loss | New errors: single / majority / unanimous (canonical classes) |
| --- | ---: | ---: | ---: | ---: |
| 9/6 | **0.000955 pp** | 0.000985 pp | 0.001267 pp | 20 / 26 / 6 |
| 8/5 | **0.001198 pp** | 0.001265 pp | 0.001530 pp | 34 / 25 / 11 |

Agreement did not improve net EV on either paytable. Unanimity prevented more bad flips but gave up too many useful flips. Stop this tuning pass and retain the single top-two reranker as the experimental recipe: deal-weighted expected RTP is **99.542950%** on 9/6 and **97.297236%** on 8/5 at five credits. These are out-of-fold estimates for the recipe, not results for a deployed checkpoint. MVP autohold remains solver-authoritative.

Local experiment artifacts: `build/whole-mask-agreement/` (`protocol.json`, `results.json`, and `agreement.py`).

### Final RTP results at five credits

The best tested standalone model on each paytable is the whole-mask ranker with one learned top-two reranker. Model RTP is the deal-weighted expected return from five-fold out-of-fold predictions covering all 2,598,960 unordered deals. The solver column gives exact optimal-play RTP on the same deals. The gap is in percentage points, calculated before rounding.

| Paytable | Exact EV solver RTP | Base ranker RTP | Final model RTP | Final gap to solver |
| --- | ---: | ---: | ---: | ---: |
| 9/6 Jacks or Better | 99.543904% | 99.541853% | **99.542950%** | 0.000955 pp |
| 8/5 Jacks or Better | 97.298434% | 97.296475% | **97.297236%** | 0.001198 pp |

Sources: the [9/6 grouped evaluation](build/whole-mask-grouped-cv/results.json) and the [final 8/5 replication](build/whole-mask-85-flips/results.json), using the ordinary reranker without a veto or voting. These results measure the training recipe, not a deployed checkpoint. Tuning is complete for this milestone; the exact solver remains authoritative for MVP autohold.
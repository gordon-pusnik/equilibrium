#ifndef TRAINER_API_H
#define TRAINER_API_H

#include <cstdint>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct VPCard {
    uint32_t suit;
    uint32_t rank;
    uint32_t held;
    uint32_t winning;
} VPCard;

typedef struct VPHandState {
    VPCard initial[5];
    VPCard final_cards[5];
    uint32_t hold_mask;
    uint32_t payout;
} VPHandState;

typedef void* VPHandle;

VPHandle vp_create(uint64_t seed);
void vp_destroy(VPHandle handle);

int vp_set_engine(VPHandle handle, const char* engine_name);
int vp_set_ml_model(VPHandle handle, const char* model_path);

int vp_deal_suggest(VPHandle handle, uint32_t bet, VPHandState* out_state);
int vp_draw_with_mask(VPHandle handle, uint32_t bet, uint32_t hold_mask, VPHandState* out_state);
int vp_play_hand(VPHandle handle, uint32_t bet, VPHandState* out_state);

double vp_calculate_optimal_play(VPHandle handle, uint32_t bet, const uint32_t* suits, const uint32_t* ranks, uint32_t* out_mask);

typedef struct VPEvaluation {
    char hand_name[64];
    uint32_t rank_value;
} VPEvaluation;

void vp_evaluate_hand(const uint32_t* suits, const uint32_t* ranks, VPEvaluation* out_eval);

typedef struct VPHoldExplanation {
    char label[64];
    char summary[192];
} VPHoldExplanation;

void vp_explain_hold(const uint32_t* suits, const uint32_t* ranks, uint32_t hold_mask, VPHoldExplanation* out_explanation);

typedef struct VPSolverAnalysis {
    uint32_t best_mask;
    uint32_t second_mask;
    double best_ev;
    double second_ev;
} VPSolverAnalysis;

int vp_analyze_solver(const uint32_t* suits, const uint32_t* ranks, uint32_t bet, VPSolverAnalysis* out_analysis);

#ifdef __cplusplus
}
#endif

#endif // TRAINER_API_H

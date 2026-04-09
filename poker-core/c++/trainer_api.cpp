#include "trainer_api.h"

#include <array>
#include <cstdint>
#include <memory>

#include <cstring>

#include "autohold.h"
#include "card.h"
#include "checkforwin.h"
#include "deck.h"
#include "hand.h"
#include "evaluator.h"

namespace {
class TrainerContext {
public:
    explicit TrainerContext(uint64_t seed)
        : m_deck(std::make_unique<Deck>()), m_have_deal(false) {
        m_deck->init(static_cast<uint32_t>(seed));
    }

    ~TrainerContext() = default;

    bool set_engine(const char* engine_name) {
        return AutoHold::set_engine(engine_name);
    }

    bool set_ml_model(const char* model_path) {
        return AutoHold::set_ml_model(model_path);
    }

    bool play_hand(uint32_t bet, VPHandState* out_state) {
        if (out_state == nullptr || bet == 0 || bet > 5) {
            return false;
        }

        m_deck->shuffle();
        m_deck->new_hand();
        m_deck->hand()->auto_hold(bet);

        auto initial_cards = m_deck->hand()->cards();
        uint32_t hold_mask = 0;
        for (uint32_t i = 0; i < 5; i++) {
            const bool held = initial_cards[i]->is_held();
            out_state->initial[i].suit = initial_cards[i]->suit();
            out_state->initial[i].rank = initial_cards[i]->rank();
            out_state->initial[i].held = held ? 1u : 0u;
            out_state->initial[i].winning = 0;
            if (held) {
                hold_mask |= (1u << i);
            }
        }
        out_state->hold_mask = hold_mask;

        m_deck->draw_cards();

        auto final_cards = m_deck->hand()->cards();
        const uint32_t win_type = CheckForWin::check_for_win(final_cards);

        for (uint32_t i = 0; i < 5; i++) {
            out_state->final_cards[i].suit = final_cards[i]->suit();
            out_state->final_cards[i].rank = final_cards[i]->rank();
            out_state->final_cards[i].held = final_cards[i]->is_held() ? 1u : 0u;
            out_state->final_cards[i].winning = final_cards[i]->is_kept() ? 1u : 0u;
        }

        switch (win_type) {
            case NONE: out_state->payout = 0; break;
            case HIGHPAIR: out_state->payout = bet * 1; break;
            case TWOPAIR: out_state->payout = bet * 2; break;
            case THREEOFAKIND: out_state->payout = bet * 3; break;
            case STRAIGHT: out_state->payout = bet * 4; break;
            case FLUSH: out_state->payout = bet * 6; break;
            case FULLHOUSE: out_state->payout = bet * 9; break;
            case FOUROFAKIND: out_state->payout = bet * 25; break;
            case STRAIGHTFLUSH: out_state->payout = bet * 50; break;
            case ROYALFLUSH: out_state->payout = (bet == 5) ? (bet * 800) : (bet * 250); break;
            default: out_state->payout = 0; break;
        }

        return true;
    }

    bool deal_suggest(uint32_t bet, VPHandState* out_state) {
        if (out_state == nullptr || bet == 0 || bet > 5) {
            return false;
        }

        m_deck->shuffle();
        m_deck->new_hand();
        m_deck->hand()->auto_hold(bet);

        auto cards = m_deck->hand()->cards();
        uint32_t hold_mask = 0;
        for (uint32_t i = 0; i < 5; i++) {
            const bool held = cards[i]->is_held();
            out_state->initial[i].suit = cards[i]->suit();
            out_state->initial[i].rank = cards[i]->rank();
            out_state->initial[i].held = held ? 1u : 0u;
            out_state->initial[i].winning = 0;
            if (held) {
                hold_mask |= (1u << i);
            }
            out_state->final_cards[i].suit = cards[i]->suit();
            out_state->final_cards[i].rank = cards[i]->rank();
            out_state->final_cards[i].held = 0;
            out_state->final_cards[i].winning = 0;
            cards[i]->set_held(false);
            cards[i]->set_kept(false);
        }

        out_state->hold_mask = hold_mask;
        out_state->payout = 0;
        m_have_deal = true;
        return true;
    }

    bool draw_with_mask(uint32_t bet, uint32_t hold_mask, VPHandState* out_state) {
        if (out_state == nullptr || bet == 0 || bet > 5 || !m_have_deal) {
            return false;
        }

        auto cards = m_deck->hand()->cards();
        for (uint32_t i = 0; i < 5; i++) {
            out_state->initial[i].suit = cards[i]->suit();
            out_state->initial[i].rank = cards[i]->rank();
            const bool held = (hold_mask & (1u << i)) != 0;
            out_state->initial[i].held = held ? 1u : 0u;
            out_state->initial[i].winning = 0;
            cards[i]->set_held(held);
        }

        m_deck->draw_cards();
        auto final_cards = m_deck->hand()->cards();
        const uint32_t win_type = CheckForWin::check_for_win(final_cards);

        for (uint32_t i = 0; i < 5; i++) {
            out_state->final_cards[i].suit = final_cards[i]->suit();
            out_state->final_cards[i].rank = final_cards[i]->rank();
            out_state->final_cards[i].held = 0;
            out_state->final_cards[i].winning = final_cards[i]->is_kept() ? 1u : 0u;
        }
        out_state->hold_mask = hold_mask;

        switch (win_type) {
            case NONE: out_state->payout = 0; break;
            case HIGHPAIR: out_state->payout = bet * 1; break;
            case TWOPAIR: out_state->payout = bet * 2; break;
            case THREEOFAKIND: out_state->payout = bet * 3; break;
            case STRAIGHT: out_state->payout = bet * 4; break;
            case FLUSH: out_state->payout = bet * 6; break;
            case FULLHOUSE: out_state->payout = bet * 9; break;
            case FOUROFAKIND: out_state->payout = bet * 25; break;
            case STRAIGHTFLUSH: out_state->payout = bet * 50; break;
            case ROYALFLUSH: out_state->payout = (bet == 5) ? (bet * 800) : (bet * 250); break;
            default: out_state->payout = 0; break;
        }

        m_have_deal = false;
        return true;
    }

    double calculate_optimal_play(uint32_t bet, const uint32_t* suits, const uint32_t* ranks, uint32_t* out_mask) {
        std::array<Card, 5> card_objs = {
            Card(suits[0], ranks[0]),
            Card(suits[1], ranks[1]),
            Card(suits[2], ranks[2]),
            Card(suits[3], ranks[3]),
            Card(suits[4], ranks[4])
        };
        std::array<Card*, 5> card_ptrs = {&card_objs[0], &card_objs[1], &card_objs[2], &card_objs[3], &card_objs[4]};
        
        double ev = 0.0;
        uint32_t mask = AutoHold::auto_hold(card_ptrs, bet, &ev);
        if (out_mask) *out_mask = mask;
        return ev;
    }

private:
    std::unique_ptr<Deck> m_deck;
    bool m_have_deal;
};
} // namespace

VPHandle vp_create(uint64_t seed) {
    return static_cast<VPHandle>(new TrainerContext(seed));
}

void vp_destroy(VPHandle handle) {
    delete static_cast<TrainerContext*>(handle);
}

int vp_set_engine(VPHandle handle, const char* engine_name) {
    if (handle == nullptr || engine_name == nullptr) return 0;
    return static_cast<TrainerContext*>(handle)->set_engine(engine_name) ? 1 : 0;
}

int vp_set_ml_model(VPHandle handle, const char* model_path) {
    if (handle == nullptr || model_path == nullptr) return 0;
    return static_cast<TrainerContext*>(handle)->set_ml_model(model_path) ? 1 : 0;
}

int vp_play_hand(VPHandle handle, uint32_t bet, VPHandState* out_state) {
    if (handle == nullptr) return 0;
    return static_cast<TrainerContext*>(handle)->play_hand(bet, out_state) ? 1 : 0;
}

int vp_deal_suggest(VPHandle handle, uint32_t bet, VPHandState* out_state) {
    if (handle == nullptr) return 0;
    return static_cast<TrainerContext*>(handle)->deal_suggest(bet, out_state) ? 1 : 0;
}

int vp_draw_with_mask(VPHandle handle, uint32_t bet, uint32_t hold_mask, VPHandState* out_state) {
    if (handle == nullptr) return 0;
    return static_cast<TrainerContext*>(handle)->draw_with_mask(bet, hold_mask, out_state) ? 1 : 0;
}

double vp_calculate_optimal_play(VPHandle handle, uint32_t bet, const uint32_t* suits, const uint32_t* ranks, uint32_t* out_mask) {
    if (handle == nullptr) return 0.0;
    return static_cast<TrainerContext*>(handle)->calculate_optimal_play(bet, suits, ranks, out_mask);
}

void vp_evaluate_hand(const uint32_t* suits, const uint32_t* ranks, VPEvaluation* out_eval) {
    if (!out_eval) return;

    std::array<Card, 5> card_objs = {
        Card(suits[0], ranks[0]),
        Card(suits[1], ranks[1]),
        Card(suits[2], ranks[2]),
        Card(suits[3], ranks[3]),
        Card(suits[4], ranks[4])
    };
    std::array<Card*, 5> card_ptrs = {&card_objs[0], &card_objs[1], &card_objs[2], &card_objs[3], &card_objs[4]};

    PokerEvaluator::Evaluation result = PokerEvaluator::evaluate_hand(card_ptrs);
    
    std::strncpy(out_eval->hand_name, result.hand_name.c_str(), sizeof(out_eval->hand_name) - 1);
    out_eval->hand_name[sizeof(out_eval->hand_name) - 1] = '\0';
    out_eval->rank_value = result.rank_value;
}

void vp_explain_hold(const uint32_t* suits, const uint32_t* ranks, uint32_t hold_mask, VPHoldExplanation* out_explanation) {
    if (!out_explanation) return;

    std::array<Card, 5> card_objs = {
        Card(suits[0], ranks[0]),
        Card(suits[1], ranks[1]),
        Card(suits[2], ranks[2]),
        Card(suits[3], ranks[3]),
        Card(suits[4], ranks[4])
    };
    std::array<Card*, 5> card_ptrs = {&card_objs[0], &card_objs[1], &card_objs[2], &card_objs[3], &card_objs[4]};

    const std::string label = AutoHold::explain_hold_label(card_ptrs, hold_mask);
    const std::string summary = AutoHold::explain_hold_summary(card_ptrs, hold_mask);

    std::strncpy(out_explanation->label, label.c_str(), sizeof(out_explanation->label) - 1);
    out_explanation->label[sizeof(out_explanation->label) - 1] = '\0';
    std::strncpy(out_explanation->summary, summary.c_str(), sizeof(out_explanation->summary) - 1);
    out_explanation->summary[sizeof(out_explanation->summary) - 1] = '\0';
}

int vp_analyze_solver(const uint32_t* suits, const uint32_t* ranks, uint32_t bet, VPSolverAnalysis* out_analysis) {
    if (!out_analysis) return 0;

    std::array<Card, 5> card_objs = {
        Card(suits[0], ranks[0]),
        Card(suits[1], ranks[1]),
        Card(suits[2], ranks[2]),
        Card(suits[3], ranks[3]),
        Card(suits[4], ranks[4])
    };
    std::array<Card*, 5> card_ptrs = {&card_objs[0], &card_objs[1], &card_objs[2], &card_objs[3], &card_objs[4]};

    uint32_t best_mask = 0;
    uint32_t second_mask = 0;
    double best_ev = 0.0;
    double second_ev = 0.0;
    if (!AutoHold::solver_top_two(card_ptrs, bet, best_mask, best_ev, second_mask, second_ev)) {
        return 0;
    }

    out_analysis->best_mask = best_mask;
    out_analysis->second_mask = second_mask;
    out_analysis->best_ev = best_ev;
    out_analysis->second_ev = second_ev;
    return 1;
}

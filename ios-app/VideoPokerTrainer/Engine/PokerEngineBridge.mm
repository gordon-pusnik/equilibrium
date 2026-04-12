#import "PokerEngineBridge.h"

#include "trainer_api.h"

@interface PokerEngineBridge ()
@property(nonatomic, assign) VPHandle handle;
@end

@implementation PokerEngineBridge

- (NSDictionary *)toDictionary:(const VPHandState&)state {
    NSMutableArray *initial = [NSMutableArray arrayWithCapacity:5];
    NSMutableArray *finalCards = [NSMutableArray arrayWithCapacity:5];

    for (int i = 0; i < 5; i++) {
        [initial addObject:@{
            @"s": @(state.initial[i].suit),
            @"r": @(state.initial[i].rank),
            @"held": @(state.initial[i].held),
            @"winning": @(state.initial[i].winning)
        }];

        [finalCards addObject:@{
            @"s": @(state.final_cards[i].suit),
            @"r": @(state.final_cards[i].rank),
            @"held": @(state.final_cards[i].held),
            @"winning": @(state.final_cards[i].winning)
        }];
    }

    return @{
        @"initial": initial,
        @"final": finalCards,
        @"holdMask": @(state.hold_mask),
        @"payout": @(state.payout)
    };
}

- (instancetype)initWithSeed:(uint64_t)seed {
    self = [super init];
    if (self) {
        _handle = vp_create(seed);
    }
    return self;
}

- (void)dealloc {
    if (_handle != nullptr) {
        vp_destroy(_handle);
        _handle = nullptr;
    }
#if !__has_feature(objc_arc)
    [super dealloc];
#endif
}

- (BOOL)setEngine:(NSString *)engineName error:(NSError * _Nullable * _Nullable)error {
    if (_handle == nullptr) {
        if (error) {
            *error = [NSError errorWithDomain:@"PokerEngine" code:1 userInfo:@{NSLocalizedDescriptionKey: @"Engine not initialized"}];
        }
        return NO;
    }
    const BOOL ok = vp_set_engine(_handle, engineName.UTF8String) == 1;
    if (!ok && error) {
        *error = [NSError errorWithDomain:@"PokerEngine" code:2 userInfo:@{NSLocalizedDescriptionKey: @"Invalid engine"}];
    }
    return ok;
}

- (BOOL)loadMlModel:(NSString *)path error:(NSError * _Nullable * _Nullable)error {
    if (_handle == nullptr) {
        if (error) {
            *error = [NSError errorWithDomain:@"PokerEngine" code:1 userInfo:@{NSLocalizedDescriptionKey: @"Engine not initialized"}];
        }
        return NO;
    }
    const BOOL ok = vp_set_ml_model(_handle, path.UTF8String) == 1;
    if (!ok && error) {
        *error = [NSError errorWithDomain:@"PokerEngine" code:3 userInfo:@{NSLocalizedDescriptionKey: @"Failed to load ML model"}];
    }
    return ok;
}

- (BOOL)setVariant:(NSString *)variantId error:(NSError * _Nullable * _Nullable)error {
    if (_handle == nullptr) {
        if (error) {
            *error = [NSError errorWithDomain:@"PokerEngine" code:1 userInfo:@{NSLocalizedDescriptionKey: @"Engine not initialized"}];
        }
        return NO;
    }
    const BOOL ok = vp_set_variant(_handle, variantId.UTF8String) == 1;
    if (!ok && error) {
        *error = [NSError errorWithDomain:@"PokerEngine" code:9 userInfo:@{NSLocalizedDescriptionKey: @"Invalid game variant"}];
    }
    return ok;
}

- (nullable NSDictionary *)dealSuggestedWithBet:(NSInteger)bet error:(NSError * _Nullable * _Nullable)error {
    if (_handle == nullptr) {
        if (error) {
            *error = [NSError errorWithDomain:@"PokerEngine" code:1 userInfo:@{NSLocalizedDescriptionKey: @"Engine not initialized"}];
        }
        return nil;
    }

    VPHandState state;
    const BOOL ok = vp_deal_suggest(_handle, (uint32_t)bet, &state) == 1;
    if (!ok) {
        if (error) {
            *error = [NSError errorWithDomain:@"PokerEngine" code:5 userInfo:@{NSLocalizedDescriptionKey: @"Failed to deal hand"}];
        }
        return nil;
    }

    return [self toDictionary:state];
}

- (nullable NSDictionary *)drawWithBet:(NSInteger)bet holdMask:(NSUInteger)holdMask error:(NSError * _Nullable * _Nullable)error {
    if (_handle == nullptr) {
        if (error) {
            *error = [NSError errorWithDomain:@"PokerEngine" code:1 userInfo:@{NSLocalizedDescriptionKey: @"Engine not initialized"}];
        }
        return nil;
    }

    VPHandState state;
    const BOOL ok = vp_draw_with_mask(_handle, (uint32_t)bet, (uint32_t)holdMask, &state) == 1;
    if (!ok) {
        if (error) {
            *error = [NSError errorWithDomain:@"PokerEngine" code:6 userInfo:@{NSLocalizedDescriptionKey: @"Failed to draw; deal a hand first"}];
        }
        return nil;
    }

    return [self toDictionary:state];
}

- (nullable NSDictionary *)playHandWithBet:(NSInteger)bet error:(NSError * _Nullable * _Nullable)error {
    if (_handle == nullptr) {
        if (error) {
            *error = [NSError errorWithDomain:@"PokerEngine" code:1 userInfo:@{NSLocalizedDescriptionKey: @"Engine not initialized"}];
        }
        return nil;
    }

    VPHandState state;
    const BOOL ok = vp_play_hand(_handle, (uint32_t)bet, &state) == 1;
    if (!ok) {
        if (error) {
            *error = [NSError errorWithDomain:@"PokerEngine" code:4 userInfo:@{NSLocalizedDescriptionKey: @"Failed to play hand"}];
        }
        return nil;
    }

    return [self toDictionary:state];
}

- (BOOL)calculateHoldMaskWithBet:(NSInteger)bet suits:(NSArray<NSNumber *> *)suits ranks:(NSArray<NSNumber *> *)ranks holdMask:(NSUInteger *)holdMask error:(NSError * _Nullable * _Nullable)error {
    if (_handle == nullptr) {
        if (error) {
            *error = [NSError errorWithDomain:@"PokerEngine" code:1 userInfo:@{NSLocalizedDescriptionKey: @"Engine not initialized"}];
        }
        return NO;
    }
    if (suits.count != 5 || ranks.count != 5) {
        if (error) {
            *error = [NSError errorWithDomain:@"PokerEngine" code:7 userInfo:@{NSLocalizedDescriptionKey: @"Exactly five cards are required"}];
        }
        return NO;
    }

    uint32_t cSuits[5];
    uint32_t cRanks[5];
    for (NSUInteger i = 0; i < 5; i++) {
        cSuits[i] = (uint32_t)suits[i].unsignedIntValue;
        cRanks[i] = (uint32_t)ranks[i].unsignedIntValue;
    }

    uint32_t outMask = 0;
    vp_calculate_optimal_play(_handle, (uint32_t)bet, cSuits, cRanks, &outMask);
    if (holdMask) {
        *holdMask = (NSUInteger)outMask;
    }
    return YES;
}

- (nullable NSDictionary *)explainHoldWithSuits:(NSArray<NSNumber *> *)suits ranks:(NSArray<NSNumber *> *)ranks holdMask:(NSUInteger)holdMask error:(NSError * _Nullable * _Nullable)error {
    if (suits.count != 5 || ranks.count != 5) {
        if (error) {
            *error = [NSError errorWithDomain:@"PokerEngine" code:7 userInfo:@{NSLocalizedDescriptionKey: @"Exactly five cards are required"}];
        }
        return nil;
    }

    uint32_t cSuits[5];
    uint32_t cRanks[5];
    for (NSUInteger i = 0; i < 5; i++) {
        cSuits[i] = (uint32_t)suits[i].unsignedIntValue;
        cRanks[i] = (uint32_t)ranks[i].unsignedIntValue;
    }

    VPHoldExplanation explanation = {};
    vp_explain_hold(cSuits, cRanks, (uint32_t)holdMask, &explanation);
    return @{
        @"category": [NSString stringWithUTF8String:explanation.category],
        @"headline": [NSString stringWithUTF8String:explanation.headline],
        @"summary": [NSString stringWithUTF8String:explanation.summary],
        @"patternTip": [NSString stringWithUTF8String:explanation.pattern_tip]
    };
}

- (nullable NSDictionary *)analyzeSolverWithBet:(NSInteger)bet suits:(NSArray<NSNumber *> *)suits ranks:(NSArray<NSNumber *> *)ranks error:(NSError * _Nullable * _Nullable)error {
    if (suits.count != 5 || ranks.count != 5) {
        if (error) {
            *error = [NSError errorWithDomain:@"PokerEngine" code:7 userInfo:@{NSLocalizedDescriptionKey: @"Exactly five cards are required"}];
        }
        return nil;
    }

    uint32_t cSuits[5];
    uint32_t cRanks[5];
    for (NSUInteger i = 0; i < 5; i++) {
        cSuits[i] = (uint32_t)suits[i].unsignedIntValue;
        cRanks[i] = (uint32_t)ranks[i].unsignedIntValue;
    }

    VPSolverAnalysis analysis = {};
    if (vp_analyze_solver(_handle, cSuits, cRanks, (uint32_t)bet, &analysis) != 1) {
        if (error) {
            *error = [NSError errorWithDomain:@"PokerEngine" code:8 userInfo:@{NSLocalizedDescriptionKey: @"Failed to analyze solver EVs"}];
        }
        return nil;
    }

    return @{
        @"bestMask": @(analysis.best_mask),
        @"secondMask": @(analysis.second_mask),
        @"bestEV": @(analysis.best_ev),
        @"secondEV": @(analysis.second_ev)
    };
}

- (nullable NSDictionary *)analyzePlayerHoldWithBet:(NSInteger)bet suits:(NSArray<NSNumber *> *)suits ranks:(NSArray<NSNumber *> *)ranks holdMask:(NSUInteger)holdMask error:(NSError * _Nullable * _Nullable)error {
    if (suits.count != 5 || ranks.count != 5) {
        if (error) {
            *error = [NSError errorWithDomain:@"PokerEngine" code:7 userInfo:@{NSLocalizedDescriptionKey: @"Exactly five cards are required"}];
        }
        return nil;
    }

    uint32_t cSuits[5];
    uint32_t cRanks[5];
    for (NSUInteger i = 0; i < 5; i++) {
        cSuits[i] = (uint32_t)suits[i].unsignedIntValue;
        cRanks[i] = (uint32_t)ranks[i].unsignedIntValue;
    }

    VPMistakeAnalysis analysis = {};
    if (vp_analyze_player_hold(_handle, cSuits, cRanks, (uint32_t)bet, (uint32_t)holdMask, &analysis) != 1) {
        if (error) {
            *error = [NSError errorWithDomain:@"PokerEngine" code:10 userInfo:@{NSLocalizedDescriptionKey: @"Failed to analyze player hold"}];
        }
        return nil;
    }

    return @{
        @"bestMask": @(analysis.best_mask),
        @"bestEV": @(analysis.best_ev),
        @"playerEV": @(analysis.player_ev),
        @"evDelta": @(analysis.ev_delta),
        @"severity": [NSString stringWithUTF8String:analysis.severity]
    };
}

@end

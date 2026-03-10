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

@end

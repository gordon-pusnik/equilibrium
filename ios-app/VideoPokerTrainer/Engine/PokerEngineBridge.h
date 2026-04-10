#import <Foundation/Foundation.h>

NS_ASSUME_NONNULL_BEGIN

@interface PokerEngineBridge : NSObject

- (instancetype)initWithSeed:(uint64_t)seed;

- (BOOL)setEngine:(NSString *)engineName error:(NSError * _Nullable * _Nullable)error;
- (BOOL)setVariant:(NSString *)variantId error:(NSError * _Nullable * _Nullable)error;
- (BOOL)loadMlModel:(NSString *)path error:(NSError * _Nullable * _Nullable)error;
- (nullable NSDictionary *)dealSuggestedWithBet:(NSInteger)bet error:(NSError * _Nullable * _Nullable)error;
- (nullable NSDictionary *)drawWithBet:(NSInteger)bet holdMask:(NSUInteger)holdMask error:(NSError * _Nullable * _Nullable)error;
- (nullable NSDictionary *)playHandWithBet:(NSInteger)bet error:(NSError * _Nullable * _Nullable)error;
- (BOOL)calculateHoldMaskWithBet:(NSInteger)bet suits:(NSArray<NSNumber *> *)suits ranks:(NSArray<NSNumber *> *)ranks holdMask:(NSUInteger *)holdMask error:(NSError * _Nullable * _Nullable)error;
- (nullable NSDictionary *)explainHoldWithSuits:(NSArray<NSNumber *> *)suits ranks:(NSArray<NSNumber *> *)ranks holdMask:(NSUInteger)holdMask error:(NSError * _Nullable * _Nullable)error;
- (nullable NSDictionary *)analyzeSolverWithBet:(NSInteger)bet suits:(NSArray<NSNumber *> *)suits ranks:(NSArray<NSNumber *> *)ranks error:(NSError * _Nullable * _Nullable)error;

@end

NS_ASSUME_NONNULL_END

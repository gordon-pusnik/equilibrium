package com.example.videopoker

object NativeBridge {
    init {
        System.loadLibrary("videopoker_native")
    }

    external fun nativeCreate(seed: Long): Long
    external fun nativeDestroy(handle: Long)
    external fun nativeSetEngine(handle: Long, engine: String): Boolean
    external fun nativeSetMlModel(handle: Long, path: String): Boolean
    external fun nativeDealSuggested(handle: Long, bet: Int): IntArray?
    external fun nativeDrawWithMask(handle: Long, bet: Int, holdMask: Int): IntArray?
    external fun nativePlayHand(handle: Long, bet: Int): IntArray?
    external fun nativeCalculateHoldMask(handle: Long, bet: Int, suits: IntArray, ranks: IntArray): Int
    external fun nativeExplainHold(suits: IntArray, ranks: IntArray, holdMask: Int): Array<String>?
    external fun nativeAnalyzeSolver(suits: IntArray, ranks: IntArray, bet: Int): DoubleArray?
}

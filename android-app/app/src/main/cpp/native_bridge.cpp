#include <jni.h>
#include <string>
#include <vector>

#include "trainer_api.h"

static jintArray toJIntArray(JNIEnv* env, const VPHandState& state) {
    std::vector<jint> out;
    // initial: 5 * 4 = 20
    // hold_mask: 1
    // payout: 1
    // final: 5 * 4 = 20
    // total: 42
    out.reserve(42);

    for (int i = 0; i < 5; i++) {
        out.push_back(static_cast<jint>(state.initial[i].suit));
        out.push_back(static_cast<jint>(state.initial[i].rank));
        out.push_back(static_cast<jint>(state.initial[i].held));
        out.push_back(static_cast<jint>(state.initial[i].winning));
    }
    out.push_back(static_cast<jint>(state.hold_mask));
    out.push_back(static_cast<jint>(state.payout));

    for (int i = 0; i < 5; i++) {
        out.push_back(static_cast<jint>(state.final_cards[i].suit));
        out.push_back(static_cast<jint>(state.final_cards[i].rank));
        out.push_back(static_cast<jint>(state.final_cards[i].held));
        out.push_back(static_cast<jint>(state.final_cards[i].winning));
    }

    jintArray arr = env->NewIntArray(static_cast<jsize>(out.size()));
    env->SetIntArrayRegion(arr, 0, static_cast<jsize>(out.size()), out.data());
    return arr;
}

extern "C" JNIEXPORT jlong JNICALL
Java_com_example_videopoker_NativeBridge_nativeCreate(JNIEnv*, jobject, jlong seed) {
    return reinterpret_cast<jlong>(vp_create(static_cast<uint64_t>(seed)));
}

extern "C" JNIEXPORT void JNICALL
Java_com_example_videopoker_NativeBridge_nativeDestroy(JNIEnv*, jobject, jlong handle) {
    vp_destroy(reinterpret_cast<VPHandle>(handle));
}

extern "C" JNIEXPORT jboolean JNICALL
Java_com_example_videopoker_NativeBridge_nativeSetEngine(JNIEnv* env, jobject, jlong handle, jstring engine) {
    const char* c_engine = env->GetStringUTFChars(engine, nullptr);
    const int ok = vp_set_engine(reinterpret_cast<VPHandle>(handle), c_engine);
    env->ReleaseStringUTFChars(engine, c_engine);
    return ok == 1 ? JNI_TRUE : JNI_FALSE;
}

extern "C" JNIEXPORT jboolean JNICALL
Java_com_example_videopoker_NativeBridge_nativeSetMlModel(JNIEnv* env, jobject, jlong handle, jstring path) {
    const char* c_path = env->GetStringUTFChars(path, nullptr);
    const int ok = vp_set_ml_model(reinterpret_cast<VPHandle>(handle), c_path);
    env->ReleaseStringUTFChars(path, c_path);
    return ok == 1 ? JNI_TRUE : JNI_FALSE;
}

extern "C" JNIEXPORT jintArray JNICALL
Java_com_example_videopoker_NativeBridge_nativePlayHand(JNIEnv* env, jobject, jlong handle, jint bet) {
    VPHandState state;
    const int ok = vp_play_hand(reinterpret_cast<VPHandle>(handle), static_cast<uint32_t>(bet), &state);
    if (ok != 1) {
        return nullptr;
    }

    return toJIntArray(env, state);
}

extern "C" JNIEXPORT jintArray JNICALL
Java_com_example_videopoker_NativeBridge_nativeDealSuggested(JNIEnv* env, jobject, jlong handle, jint bet) {
    VPHandState state;
    const int ok = vp_deal_suggest(reinterpret_cast<VPHandle>(handle), static_cast<uint32_t>(bet), &state);
    if (ok != 1) {
        return nullptr;
    }
    return toJIntArray(env, state);
}

extern "C" JNIEXPORT jintArray JNICALL
Java_com_example_videopoker_NativeBridge_nativeDrawWithMask(JNIEnv* env, jobject, jlong handle, jint bet, jint holdMask) {
    VPHandState state;
    const int ok = vp_draw_with_mask(
        reinterpret_cast<VPHandle>(handle),
        static_cast<uint32_t>(bet),
        static_cast<uint32_t>(holdMask),
        &state);
    if (ok != 1) {
        return nullptr;
    }
    return toJIntArray(env, state);
}

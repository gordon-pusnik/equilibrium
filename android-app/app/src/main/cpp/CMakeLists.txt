cmake_minimum_required(VERSION 3.22.1)
project(videopoker_native)

set(ROOT_DIR ${CMAKE_CURRENT_SOURCE_DIR}/../../../../../)
set(ENGINE_DIR ${ROOT_DIR}/poker-core/c++)

add_library(videopoker_native SHARED
    native_bridge.cpp
    ${ENGINE_DIR}/card.cpp
    ${ENGINE_DIR}/deck.cpp
    ${ENGINE_DIR}/hand.cpp
    ${ENGINE_DIR}/checkforwin.cpp
    ${ENGINE_DIR}/autohold.cpp
    ${ENGINE_DIR}/game_variant.cpp
    ${ENGINE_DIR}/trainer_api.cpp
    ${ENGINE_DIR}/evaluator.cpp
)

target_include_directories(videopoker_native PRIVATE
    ${ENGINE_DIR}
)

find_library(log-lib log)

target_link_libraries(videopoker_native ${log-lib})

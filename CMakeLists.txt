cmake_minimum_required(VERSION 3.16)
project(IndustrialistFactoryPlanner CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

add_executable(industrialist_planner
    src/main.cpp
 "src/solver/Solver.cpp")

target_include_directories(industrialist_planner PRIVATE
    src
    deps
)

target_compile_options(industrialist_planner PRIVATE
    $<$<CXX_COMPILER_ID:GNU,Clang>:-Wall -Wextra>
    $<$<CXX_COMPILER_ID:MSVC>:/W4>
)
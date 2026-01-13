#pragma once
#include "hooking.h"
#include "cocos/cocos2dx/include/cocos2d.h"
#include "cocos/cocos2dx/include/cocos2dExt.h"
#include "patch.h"

#define cpatch(addr, val) addPatch("libgame.so", addr, val)
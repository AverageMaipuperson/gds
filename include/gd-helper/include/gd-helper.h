#include <cocos2d.h>
#include <android/ndk-version.h>

#if defined(__NDK_MAJOR__) && __NDK_MAJOR__ < 17
    #if __NDK_MAJOR__ >= 17
        #include "string-helper/VoidString.h"
    #endif
#elif defined(_MSC_VER) && !defined(__clang__)
    #include "string-helper/VoidString.h"

#elif defined(__clang__)
    #include "string-helper/VoidString.h"

#elif defined(__GNUC__) || defined(__GNUG__)
    #include "string-helper/VoidString.h"
#endif

#include "offset-helper/OffsetHelper.h"
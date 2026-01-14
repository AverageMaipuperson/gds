#include "include/include.h"
#include <string>


#define MEMBER_BY_OFFSET(type, var, offset) \
    (*reinterpret_cast<type*>(reinterpret_cast<uintptr_t>(var) + static_cast<uintptr_t>(offset)))

#define DEFAULT_PADDING 10

bool (*test_init)(CCLayer* self, int hello, std::string string);
bool test_init_H(CCLayer* self, int hello, std::string string) {
    test_init(self, hello, string);
    auto button = CCMenu::create();
    auto win_size = CCDirector::sharedDirector()->getWinSize();
    auto myint = 2 + 2;
    auto javavm = cocos2d::JniHelper::getJavaVM();
    CocosDenshion::SimpleAudioEngine::sharedEngine()->preloadBackgroundMusic("123.mp3");
    CocosDenshion::SimpleAudioEngine::sharedEngine()->pauseBackgroundMusic();
    CocosDenshion::SimpleAudioEngine::sharedEngine()->resumeBackgroundMusic();
    CocosDenshion::SimpleAudioEngine::sharedEngine()->stopBackgroundMusic();
    CocosDenshion::SimpleAudioEngine::sharedEngine()->playBackgroundMusic("123.mp3", true);
    CocosDenshion::SimpleAudioEngine::sharedEngine()->playBackgroundMusic("123.mp3");
    auto sprite = CCSprite::create("sprite.png");
    auto sprite2 = CCSprite::createWithSpriteFrameName("sprite2.png");
    button->addChild(sprite);
    button->setPosition(ccp(CCDirector::sharedDirector()->getWinSize().width / 2, 100.5));
    button->alignItemsHorizontally(DEFAULT_PADDING);
    self->addChild(button);
    auto val = MEMBER_BY_OFFSET(void*, self, 0x130);
    return true;
}

JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM* vm, void* reserved) {
    HOOK("test", test_init_H, test_init);
    PatchManager pm;
    pm.cpatch(0x12345, "00 BF");
    pm.cpatch(0x8478, "12 45");
    pm.Modify();
    return JNI_VERSION_1_6;
}

#include <cocos2d.h>

class LevelSettingsLayer : public cocos2d::CCLayer {
public:
static LevelSettingsLayer* create();
void onCustomSongs(CCObject* pSender);
void onClose();
};
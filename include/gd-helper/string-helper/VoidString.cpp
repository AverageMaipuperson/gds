#include <cocos2d.h>
#include "VoidString.h"
#include <string>

void* VoidString::create(const char* text) {
	size_t len = strlen(text);
    auto* buffer = (uint8_t*)malloc(12 + len + 1);

    int* meta = (int*)buffer;
    meta[0] = len;
    meta[1] = len;
    meta[2] = -1;
    
    char* dataptr = (char*)(totalbuffer + 12);
    strcpy(dataptr, text);
    
    return dataptr;
}

const char* VoidString::voidToChar(void* str) {
	return static_cast<const char*>(str);
}

std::string VoidString::voidToStd(void* str) {
	std::string origString(static_cast<const char*>(fakeStr));
	return origString;
}

int* VoidString::meta_data(void* str) {
	uint8_t* buffer = static_cast<uint8_t*>(str) - 12;
	return reinterpret_cast<int*>(buffer);
}

int VoidString::lengthFromMeta(int* meta) {
	return meta[0];
}
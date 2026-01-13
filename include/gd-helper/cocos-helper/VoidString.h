#include <cocos2d.h>
#include <string>

// only needed if you use a compiler that changes std::string signature (ndk r17+, MSVC, clang, GCC)

class VoidString {
	public:

	void* create(const char*);

	const char* voidToChar(void*);

	std::string voidToStd(void*);

	int* meta_data(void*);

	int lengthFromMeta(int*);
};
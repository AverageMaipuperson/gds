#include <cocos2d.h>
#include <string>
#include <cstdint>

class OffsetHelper {
	public:
	template <typename T>
    static T& memberByOffset(void* base, size_t offset) {
        uintptr_t baseAddr = reinterpret_cast<uintptr_t>(base);
        return *reinterpret_cast<T*>(baseAddr + offset);
    }
    template <typename T>
    static const T& memberByOffset(const void* base, size_t offset) {
        uintptr_t baseAddr = reinterpret_cast<uintptr_t>(base);
        return *reinterpret_cast<const T*>(baseAddr + offset);
    }
	template <typename Ret, typename... Args>
    static Ret funcFromOffset(void* instance, size_t vtableOffset, Args... args) {
        uintptr_t vtable = *reinterpret_cast<uintptr_t*>(instance);
        using FunctionType = Ret(*)(void*, Args...);
        FunctionType func = *reinterpret_cast<FunctionType*>(vtable + vtableOffset);
        return func(instance, args...);
    }
};
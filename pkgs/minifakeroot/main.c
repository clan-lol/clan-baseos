#include <stdint.h>
#ifdef __APPLE__
#include <unistd.h>
#endif

typedef uint32_t uid_t;

#ifdef __APPLE__
struct dyld_interpose {
  const void *replacement;
  const void *replacee;
};
#define WRAPPER(ret, name) static ret _fakeroot_wrapper_##name
#define WRAPPER_DEF(name)                                                      \
  __attribute__((                                                              \
      used)) static struct dyld_interpose _fakeroot_interpose_##name           \
      __attribute__((section("__DATA,__interpose"))) = {                       \
          &_fakeroot_wrapper_##name, &name};
#else
#define WRAPPER(ret, name) ret name
#define WRAPPER_DEF(name)
#endif

WRAPPER(uid_t, geteuid)(const char *path, int flags, ...) {
  return 0; // Fake root
}
WRAPPER_DEF(geteuid)

WRAPPER(uid_t, getuid)(const char *path, int flags, ...) {
  return 0; // Fake root
}
WRAPPER_DEF(getuid)

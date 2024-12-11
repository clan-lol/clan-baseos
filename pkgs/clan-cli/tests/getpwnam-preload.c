#define _GNU_SOURCE
#include <dlfcn.h>
#include <pwd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>

typedef struct passwd *(*getpwnam_type)(const char *name);

struct passwd *getpwnam(const char *name) {
  struct passwd *pw;
  getpwnam_type orig_getpwnam;
  orig_getpwnam = (getpwnam_type)dlsym(RTLD_NEXT, "getpwnam");
  pw = orig_getpwnam(name);

  if (pw) {
    const char *shell = getenv("LOGIN_SHELL");
    if (!shell) {
      fprintf(stderr, "no LOGIN_SHELL set\n");
      exit(1);
    }
    pw->pw_shell = strdup(shell);
  }
  return pw;
}

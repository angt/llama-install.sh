#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
#include <process.h>
#define execv _execv
#else
#include <unistd.h>
#endif

int
main(int argc, char **argv)
{
    char *last = NULL;

    for (char *p = argv[0]; p = strstr(p, "zig-"), p; p++)
        last = p;

    char *sub = NULL;
    char *ext = NULL;
    size_t n = 0;

    if (last) {
        sub = last + 4;
        while (sub[n] && sub[n] != '.')
            n++;
        ext = sub + n;
    }
    if (!n) {
        fprintf(stderr, "zig: cannot derive subcommand from %s\n", argv[0]);
        return 1;
    }
    size_t dirlen = (size_t)(last - argv[0]);
    size_t extlen = strlen(ext);
    char *zig = malloc(dirlen + 3 + extlen + 1);

    if (!zig) {
        perror("malloc");
        return 1;
    }
    memcpy(zig, argv[0], dirlen);
    memcpy(zig + dirlen, "zig", 3);
    memcpy(zig + dirlen + 3, ext, extlen + 1);

    char **args = malloc((size_t)(argc + 2) * sizeof(*args));

    if (!args) {
        perror("malloc");
        return 1;
    }
    sub[n] = '\0';
    args[0] = zig;
    args[1] = sub;
    memcpy(args + 2, argv + 1, (size_t)argc * sizeof(*args));

    execv(zig, args);
    perror(zig);
    return 1;
}

/* equ_path.c -- what a path names, for the file checks of libequapi.so
 * (equ_api.f90: host_file_refusal). Not part of the C interface
 * (equ_api.h): the symbol is hidden in the shared library.
 *
 * 0  the name does not exist (ENOENT)
 * 1  a regular file
 * 2  something else: a directory, pipe, FIFO, socket, terminal, device
 * 3  a regular file that is the process's standard input, output or
 *    error (the same device and inode as fd 0, 1 or 2)
 * 4  stat(2) failed otherwise: a loop of links, a name too long, a part
 *    that is not a directory, no access
 *
 * stat(2) follows symbolic links, so /dev/stdin, /proc/self/fd/0 and any
 * link to them give the kind of the file they reach.
 */
#include <errno.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>

static int is_std_stream(const struct stat *st)
{
    struct stat sf;
    int fd;

    for (fd = 0; fd <= 2; fd++)
        if (fstat(fd, &sf) == 0 && sf.st_dev == st->st_dev && sf.st_ino == st->st_ino)
            return 1;
    return 0;
}

__attribute__((visibility("hidden")))
int equ_path_kind(const char *path)
{
    struct stat st, so;
    int fd, k;

    if (stat(path, &st) != 0)
        return errno == ENOENT ? 0 : 4;
    if (!S_ISREG(st.st_mode))
        return 2;
    /* The file as an open reaches it. On macOS /dev/fd/N (and a link to
     * it) duplicates descriptor N, and stat(2) of it reports the inode of
     * the file but the st_dev of /dev/fd: the file is opened (without
     * blocking, creating or truncating it) and the descriptor compared. */
    fd = open(path, O_RDONLY | O_NONBLOCK | O_NOCTTY | O_CLOEXEC);
    if (fd < 0)
        fd = open(path, O_WRONLY | O_NONBLOCK | O_NOCTTY | O_CLOEXEC);
    if (fd >= 0) {
        k = fstat(fd, &so);
        close(fd);
        if (k == 0) {
            if (!S_ISREG(so.st_mode))
                return 2;
            if (is_std_stream(&so))
                return 3;
        }
    }
    return is_std_stream(&st) ? 3 : 1;
}

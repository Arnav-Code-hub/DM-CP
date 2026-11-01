#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_V 10
#define INF (LLONG_MAX / 4)

static void number(long long value) {
    if (value == INF) printf("null");
    else printf("%lld", value);
}

static void matrix_json(long long matrix[MAX_V][MAX_V], int n) {
    putchar('[');
    for (int i = 0; i < n; i++) {
        printf("%s[", i ? "," : "");
        for (int j = 0; j < n; j++) {
            if (j) putchar(',');
            number(matrix[i][j]);
        }
        putchar(']');
    }
    putchar(']');
}

static int integer(const char *token, long long *value) {
    char *end;
    errno = 0;
    *value = strtoll(token, &end, 10);
    return !errno && end != token && *end == '\0';
}

int main(void) {
    char algorithm[64], token[64];
    long long size, weight;
    long long distance[MAX_V][MAX_V] = {{0}}, previous[MAX_V][MAX_V];
    int next[MAX_V][MAX_V], previous_next[MAX_V][MAX_V];
    int affected[MAX_V][MAX_V] = {{0}};

    if (scanf("%63s %63s", algorithm, token) != 2 ||
        !integer(token, &size) || size < 1 || size > MAX_V ||
        (strcmp(algorithm, "warshall") && strcmp(algorithm, "floyd"))) {
        fprintf(stderr, "Expected: warshall or floyd, then vertex count 1..10.\n");
        return 1;
    }
    int n = (int)size;
    int warshall = !strcmp(algorithm, "warshall");
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            if (scanf("%63s", token) != 1 ||
                (strcmp(token, "x") && (!integer(token, &weight) ||
                                        weight < -1000 || weight > 1000))) {
                fprintf(stderr, "Expected an n by n matrix: x or integer -1000..1000.\n");
                return 1;
            }
            int edge = strcmp(token, "x") != 0;
            if (warshall) distance[i][j] = edge || i == j;
            else distance[i][j] = edge ? weight : INF;
            if (!warshall && i == j && distance[i][j] > 0) distance[i][j] = 0;
            next[i][j] = edge || i == j ? j : -1;
        }
    }
    if (scanf("%63s", token) != EOF) {
        fprintf(stderr, "Unexpected data after the matrix.\n");
        return 1;
    }

    printf("{\"algorithm\":\"%s\",\"initial\":", algorithm);
    matrix_json(distance, n);
    printf(",\"steps\":[");
    for (int k = 0; k < n; k++) {
        /* Read the previous stage so the trace matches the stated recurrence. */
        memcpy(previous, distance, sizeof distance);
        memcpy(previous_next, next, sizeof next);
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                long long old = previous[i][j];
                long long left = previous[i][k], right = previous[k][j];
                long long candidate = warshall ? (left && right) :
                    (left == INF || right == INF ? INF : left + right);
                long long value = warshall ? (old || candidate) :
                    (candidate < old ? candidate : old);
                distance[i][j] = value;
                if (!warshall && value < old) next[i][j] = previous_next[i][k];
                if (k || i || j) putchar(',');
                printf("{\"k\":%d,\"i\":%d,\"j\":%d,\"old\":", k, i, j);
                number(old);
                printf(",\"left\":"); number(left);
                printf(",\"right\":"); number(right);
                printf(",\"candidate\":"); number(candidate);
                printf(",\"value\":"); number(value);
                printf(",\"changed\":%s}", value != old ? "true" : "false");
            }
        }
    }
    printf("],\"final\":");
    matrix_json(distance, n);

    if (!warshall) {
        for (int k = 0; k < n; k++) {
            if (distance[k][k] < 0) {
                for (int i = 0; i < n; i++)
                    for (int j = 0; j < n; j++)
                        if (distance[i][k] != INF && distance[k][j] != INF)
                            affected[i][j] = 1;
            }
        }
        printf(",\"affected\":[");
        for (int i = 0; i < n; i++) {
            printf("%s[", i ? "," : "");
            for (int j = 0; j < n; j++)
                printf("%s%s", j ? "," : "", affected[i][j] ? "true" : "false");
            putchar(']');
        }
        printf("],\"paths\":[");
        for (int i = 0; i < n; i++) {
            printf("%s[", i ? "," : "");
            for (int j = 0; j < n; j++) {
                if (j) putchar(',');
                if (affected[i][j] || distance[i][j] == INF) {
                    printf("null");
                    continue;
                }
                int path[MAX_V + 1], length = 1, vertex = i;
                path[0] = i;
                while (vertex != j && length <= n) {
                    vertex = next[vertex][j];
                    if (vertex < 0 || vertex >= n) break;
                    path[length++] = vertex;
                }
                if (vertex != j) printf("null");
                else {
                    putchar('[');
                    for (int p = 0; p < length; p++) printf("%s%d", p ? "," : "", path[p]);
                    putchar(']');
                }
            }
            putchar(']');
        }
        putchar(']');
    }
    puts("}");
    return 0;
}

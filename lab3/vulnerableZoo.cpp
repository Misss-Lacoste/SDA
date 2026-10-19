#include <iostream>
#include <fstream>
#include <string>
#include <cstring>
#include <cstdio>
#include <vector>
#include <zlib.h>   // zlib 1.2.11  (CVE-2018-25032, CVE-2022-37434)

struct Animal {
    char name[32];
    char species[32];
    int  age;
};

void processAnimal(const Animal& a) {
    char buf[16];
    strcpy(buf, a.name);              // BUG-1: buffer overflow (ошибка памяти)
    printf(a.species);                // BUG-2: format string
    printf(" age=%d\n", a.age);
}

void compress(const char* data, size_t len) {
    z_stream s{};
    deflateInit(&s, Z_DEFAULT_COMPRESSION);
    s.next_in  = (Bytef*)data;
    s.avail_in = len;
    Bytef out[256];
    do { s.next_out = out; s.avail_out = sizeof(out); deflate(&s, Z_FINISH); }
    while (s.avail_out == 0);
    deflateEnd(&s);
}

int main(int argc, char** argv) {
    std::istream* in = &std::cin;
    std::ifstream f;
    if (argc > 1) { f.open(argv[1]); in = &f; }

    std::vector<Animal> zoo;
    std::string line;
    while (std::getline(*in, line)) {
        if (line.empty()) continue;
        Animal a{};
        std::sscanf(line.c_str(), "%[^,],%[^,],%d", a.name, a.species, &a.age);
        zoo.push_back(a);
        compress(a.name, std::strlen(a.name));
    }
    for (auto& a : zoo) processAnimal(a);
    return 0;
}
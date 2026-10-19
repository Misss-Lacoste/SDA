#include <iostream>
#include <fstream>
#include <string>
#include <cstring>
#include <vector>
#include <zlib.h>   // zlib >= 1.3.1

struct Animal { std::string name, species; int age; };

void processAnimal(const Animal& a) {
    std::string safe = a.name.substr(0, 15);   // явное усечение
    std::cout << "name=" << safe << " ";
    std::cout << "species=" << a.species << " "; // никаких format-string
    std::cout << "age=" << a.age << "\n";
}

int compress(const std::string& data) {
    z_stream s{};
    if (deflateInit(&s, Z_DEFAULT_COMPRESSION) != Z_OK) return -1;
    s.next_in  = (Bytef*)data.data();
    s.avail_in = data.size();
    Bytef out[256];
    do { s.next_out = out; s.avail_out = sizeof(out);
         if (deflate(&s, Z_FINISH) == Z_STREAM_ERROR) { deflateEnd(&s); return -1; }
    } while (s.avail_out == 0);
    deflateEnd(&s);
    return 0;
}

int main(int argc, char** argv) {
    std::istream* in = &std::cin;
    std::ifstream f;
    if (argc > 1) { f.open(argv[1]); if (!f) return 1; in = &f; }

    std::vector<Animal> zoo;
    std::string line;
    while (std::getline(*in, line)) {
        if (line.empty()) continue;
        Animal a;
        size_t p1 = line.find(','), p2 = line.find(',', p1+1);
        if (p1 == std::string::npos || p2 == std::string::npos) continue;
        a.name    = line.substr(0, p1);
        a.species = line.substr(p1+1, p2-p1-1);
        try { a.age = std::stoi(line.substr(p2+1)); } catch(...) { continue; }
        zoo.push_back(a);
        compress(a.name);
    }
    for (auto& a : zoo) processAnimal(a);
    return 0;
}
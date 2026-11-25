#include <iostream>

int main() {
    int first = 0;
    int second = 0;

    std::cout << "Enter two integers: ";
    if (!(std::cin >> first >> second)) {
        std::cerr << "Invalid input.\n";
        return 1;
    }

    const long long sum = static_cast<long long>(first) + second;
    std::cout << "Sum: " << sum << '\n';
    std::cout << "(checked by JiangGengrui)\n";
    return 0;
}

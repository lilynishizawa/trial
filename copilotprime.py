import math


def sieve_of_eratosthenes(limit):
    sieve = [True] * (limit + 1)
    sieve[0:2] = [False, False]

    for i in range(2, int(limit**0.5) + 1):
        if sieve[i]:
            for multiple in range(i * i, limit + 1, i):
                sieve[multiple] = False

    return [i for i, is_prime in enumerate(sieve) if is_prime]


def first_n_primes(n):
    if n <= 0:
        return []
    if n == 1:
        return [2]

    estimate = int(n * (math.log(n) + math.log(math.log(n)))) + 10
    primes = sieve_of_eratosthenes(estimate)

    while len(primes) < n:
        estimate *= 2
        primes = sieve_of_eratosthenes(estimate)

    return primes[:n]


if __name__ == "__main__":
    target = 20
    for prime in first_n_primes(target):
        print(prime)

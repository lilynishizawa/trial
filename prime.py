def primenum(n):
    if n < 2:
        return False
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False
    return True

count = 0
num = 2
target = 20

while count < target:
    if primenum(num):
        print(num)
        count += 1
    num += 1
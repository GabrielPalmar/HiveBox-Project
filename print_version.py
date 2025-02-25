def print_version():
    with open('version.txt', 'r') as f:
        version = f.read()
    print(f"Current app version: {version}")

if __name__ == '__main__':
    print_version()
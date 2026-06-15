from asd import StealthLoaderGenerator

def main():
    gen = StealthLoaderGenerator()
    # small test payload and key
    encrypted = b"ABCD"
    key = b"0123456789abcdef0123456789abcdef"
    metadata = {
        'CompanyName': 'Acme"Corp',
        'ProductName': 'Prod',
        'FileDescription': 'Desc',
        'OriginalFilename': 'out.exe'
    }
    try:
        c = gen.generate_stealth_loader(encrypted, key, len(encrypted), metadata)
        out = 'test_loader_out.c'
        with open(out, 'w', encoding='utf-8') as f:
            f.write(c)
        print('OK: wrote', out)
    except Exception as e:
        print('ERROR:', e)

if __name__ == '__main__':
    main()

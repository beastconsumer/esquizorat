import ast
import sys

files = [
    'Program.py',
    'central_client.py',
    'web_api_docker.py',
    'builder2.py'
]

for file in files:
    try:
        with open(file, encoding='utf-8') as f:
            ast.parse(f.read())
        print(f'{file}: OK')
    except SyntaxError as e:
        print(f'{file}: ERRO - Linha {e.lineno}: {e.msg}')
    except Exception as e:
        print(f'{file}: ERRO - {e}')

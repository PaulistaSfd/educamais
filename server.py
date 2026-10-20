#!/usr/bin/env python3
import http.server
import socketserver
import json
import urllib.parse
import urllib.request
import os
from pathlib import Path

PORT = 3000

# Load .env file
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            if '=' in line:
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

APELA_USER = os.getenv('APELA_API_USER', 'seu_token_aqui').strip()
LUMEAPAG_API_KEY = os.getenv('LUMEAPAG_API_KEY', '').strip()
LUMEAPAG_WEBHOOK_SECRET = os.getenv('LUMEAPAG_WEBHOOK_SECRET', '').strip()

# Debug: Print loaded credentials
if LUMEAPAG_API_KEY:
    print(f'[INFO] LUMEAPAG_API_KEY carregada (tamanho: {len(LUMEAPAG_API_KEY)} chars)', flush=True)
else:
    print('[WARN] LUMEAPAG_API_KEY não encontrada no .env', flush=True)

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Parse URL
        parsed_url = urllib.parse.urlparse(self.path)

        # Handle API routes
        if parsed_url.path == '/api/consultar-cpf':
            return self.handle_consultar_cpf(parsed_url)
        elif parsed_url.path == '/api/consultar-transacao':
            return self.handle_consultar_transacao(parsed_url)

        # Serve static files
        return super().do_GET()

    def do_POST(self):
        # Parse URL
        parsed_url = urllib.parse.urlparse(self.path)

        # Handle API routes
        if parsed_url.path == '/api/criar-cobranca':
            return self.handle_criar_cobranca()

        # Default: not found
        self.send_json_response(404, {'status': 404, 'erro': 'Endpoint não encontrado'})

    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def handle_consultar_cpf(self, parsed_url):
        """Handle CPF consultation API"""
        try:
            # Get CPF from query parameters
            query_params = urllib.parse.parse_qs(parsed_url.query)
            cpf = query_params.get('cpf', [''])[0]

            # Remove non-digits from CPF
            cpf_clean = ''.join(filter(str.isdigit, cpf))

            if not cpf_clean or len(cpf_clean) != 11:
                self.send_json_response(400, {'status': 400, 'erro': 'CPF não informado ou inválido'})
                return

            # Call APELA API
            apela_url = f'https://api-apela.online/?user={urllib.parse.quote(APELA_USER)}&cpf={urllib.parse.quote(cpf_clean)}'

            try:
                request = urllib.request.Request(
                    apela_url,
                    headers={'User-Agent': 'Mozilla/5.0 (compatible; EducacaoBR/1.0)'}
                )
                with urllib.request.urlopen(request, timeout=10) as response:
                    apela_response = json.loads(response.read().decode('utf-8'))
                    print(f'[DEBUG] Resposta APELA completa: {json.dumps(apela_response, ensure_ascii=False)}')

                # Check if APELA returned success
                if apela_response.get('status') != 200:
                    error_msg = apela_response.get('erro', 'CPF não encontrado')
                    self.send_json_response(404, {'status': 404, 'erro': error_msg})
                    return

                # Check if name exists
                if not apela_response.get('nome') or apela_response.get('nome').strip() == '':
                    self.send_json_response(404, {'status': 404, 'erro': 'CPF não encontrado'})
                    return

                # Return success with data
                self.send_json_response(200, {
                    'status': 200,
                    'nome': apela_response.get('nome', ''),
                    'cpf': cpf_clean,
                    'nascimento': apela_response.get('nascimento', ''),
                    'mae': apela_response.get('mae', ''),
                    'sexo': apela_response.get('sexo', '')
                })

            except urllib.error.HTTPError as e:
                self.send_json_response(502, {'status': 502, 'erro': 'Falha na consulta. Tente novamente.'})
            except urllib.error.URLError as e:
                self.send_json_response(503, {'status': 503, 'erro': 'Serviço indisponível'})
            except Exception as e:
                print(f'[consultar-cpf] Erro: {e}')
                self.send_json_response(500, {'status': 500, 'erro': 'Erro interno do servidor'})

        except Exception as e:
            print(f'[api] Erro geral: {e}')
            self.send_json_response(500, {'status': 500, 'erro': 'Erro interno do servidor'})

    def handle_criar_cobranca(self):
        """Handle LumeaPag charge creation"""
        try:
            # Check if API key is configured
            if not LUMEAPAG_API_KEY:
                self.send_json_response(500, {'status': 500, 'erro': 'LUMEAPAG_API_KEY não configurada'})
                return

            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            payload = json.loads(body.decode('utf-8'))

            # Call LumeaPag API
            lumeapag_url = 'https://lumeapag.com/api/gateway/charges'

            # Debug key
            key_preview = f"{LUMEAPAG_API_KEY[:10]}...{LUMEAPAG_API_KEY[-10:]}" if len(LUMEAPAG_API_KEY) > 20 else "***"
            print(f'[DEBUG] Enviando requisição para LumeaPag com chave: {key_preview}', flush=True)
            print(f'[DEBUG] Payload: {json.dumps(payload, ensure_ascii=False)}', flush=True)

            request = urllib.request.Request(
                lumeapag_url,
                data=json.dumps(payload).encode('utf-8'),
                headers={
                    'Content-Type': 'application/json',
                    'X-Api-Key': LUMEAPAG_API_KEY,
                    'Idempotency-Key': payload.get('metadata', {}).get('pedido', 'no-key'),
                    'User-Agent': 'LojaDrop/1.0'
                },
                method='POST'
            )

            try:
                with urllib.request.urlopen(request, timeout=10) as response:
                    lumeapag_response = json.loads(response.read().decode('utf-8'))
                    print(f'[DEBUG] Resposta LumeaPag: {json.dumps(lumeapag_response, ensure_ascii=False)}')

                    if lumeapag_response.get('success'):
                        self.send_json_response(200, lumeapag_response)
                    else:
                        self.send_json_response(400, {'status': 400, 'erro': 'Falha ao criar cobrança', 'data': lumeapag_response})

            except urllib.error.HTTPError as e:
                error_body = e.read().decode('utf-8')
                print(f'[criar-cobranca] HTTP Error {e.code}: {error_body}')
                try:
                    error_data = json.loads(error_body)
                    self.send_json_response(e.code, {'status': e.code, 'erro': error_data})
                except:
                    self.send_json_response(e.code, {'status': e.code, 'erro': error_body})

            except urllib.error.URLError as e:
                self.send_json_response(503, {'status': 503, 'erro': 'Serviço indisponível'})
            except Exception as e:
                print(f'[criar-cobranca] Erro: {e}')
                self.send_json_response(500, {'status': 500, 'erro': 'Erro interno do servidor'})

        except json.JSONDecodeError:
            self.send_json_response(400, {'status': 400, 'erro': 'JSON inválido'})
        except Exception as e:
            print(f'[api] Erro geral: {e}')
            self.send_json_response(500, {'status': 500, 'erro': 'Erro interno do servidor'})

    def handle_consultar_transacao(self, parsed_url):
        """Handle LumeaPag transaction query"""
        try:
            # Check if API key is configured
            if not LUMEAPAG_API_KEY:
                self.send_json_response(500, {'status': 500, 'erro': 'LUMEAPAG_API_KEY não configurada'})
                return

            # Get transaction ID from query parameters
            query_params = urllib.parse.parse_qs(parsed_url.query)
            transaction_id = query_params.get('id', [''])[0]

            if not transaction_id:
                self.send_json_response(400, {'status': 400, 'erro': 'ID da transação não informado'})
                return

            # Call LumeaPag API
            lumeapag_url = f'https://lumeapag.com/api/gateway/charges/{transaction_id}'

            request = urllib.request.Request(
                lumeapag_url,
                headers={
                    'Content-Type': 'application/json',
                    'X-Api-Key': LUMEAPAG_API_KEY
                },
                method='GET'
            )

            try:
                with urllib.request.urlopen(request, timeout=10) as response:
                    lumeapag_response = json.loads(response.read().decode('utf-8'))
                    print(f'[DEBUG] Consulta LumeaPag: {json.dumps(lumeapag_response, ensure_ascii=False)}')
                    self.send_json_response(200, lumeapag_response)

            except urllib.error.HTTPError as e:
                error_body = e.read().decode('utf-8')
                print(f'[consultar-transacao] HTTP Error {e.code}: {error_body}')
                try:
                    error_data = json.loads(error_body)
                    self.send_json_response(e.code, {'status': e.code, 'erro': error_data})
                except:
                    self.send_json_response(e.code, {'status': e.code, 'erro': error_body})

            except urllib.error.URLError as e:
                self.send_json_response(503, {'status': 503, 'erro': 'Serviço indisponível'})
            except Exception as e:
                print(f'[consultar-transacao] Erro: {e}')
                self.send_json_response(500, {'status': 500, 'erro': 'Erro interno do servidor'})

        except Exception as e:
            print(f'[api] Erro geral: {e}')
            self.send_json_response(500, {'status': 500, 'erro': 'Erro interno do servidor'})

    def send_json_response(self, status_code, data):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        response_json = json.dumps(data, ensure_ascii=False)
        self.wfile.write(response_json.encode('utf-8'))

if __name__ == '__main__':
    handler = CustomHTTPRequestHandler
    # Change to the project directory
    os.chdir(Path(__file__).parent)

    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"Server running at http://localhost:{PORT}")
        httpd.serve_forever()

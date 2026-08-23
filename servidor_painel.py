"""
Servidor Híbrido (Local HD + Nuvem Render) para o Painel de Acompanhamento
Cria e gerencia automaticamente o arquivo dados_painel.json.
"""

import http.server
import socketserver
import os
import sys
import json
import webbrowser

# Lê a porta enviada pelo Render (PORT) ou usa 8000 se rodar no HD local
PORT = int(os.environ.get("PORT", sys.argv[1] if len(sys.argv) > 1 else 8000))
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_DADOS = os.path.join(DIRECTORY, 'dados_painel.json')

def garantir_arquivo_dados():
    if not os.path.exists(ARQUIVO_DADOS):
        estrutura_inicial = {
            "db": {
                "obras": []
            },
            "revision": 1
        }
        with open(ARQUIVO_DADOS, 'w', encoding='utf-8') as f:
            json.dump(estrutura_inicial, f, ensure_ascii=False, indent=2)
        print(f"✨ Arquivo de dados criado em: {ARQUIVO_DADOS}")

class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Servidor HTTP com suporte a gravação (POST) e CORS liberado para o Render."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('directory', DIRECTORY)
        super().__init__(*args, **kwargs)

    def end_headers(self):
        # Libera acesso para a API da nuvem e localhost sem dar erro de CORS
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        if self.path in ['/api/salvar', '/api/db']:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)

            try:
                dados = json.loads(post_data.decode('utf-8'))

                with open(ARQUIVO_DADOS, 'w', encoding='utf-8') as f:
                    json.dump(dados, f, ensure_ascii=False, indent=2)

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "sucesso", "mensagem": "Salvo com sucesso!"}).encode('utf-8'))
                print("💾 [SERVIDOR] Dados gravados no 'dados_painel.json'!")

            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "erro", "mensagem": str(e)}).encode('utf-8'))
        else:
            self.send_error(404, "Rota não encontrada")


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def is_port_in_use(port):
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def main():
    global PORT

    garantir_arquivo_dados()

    # Se estiver rodando localmente no HD e a porta estiver em uso, busca a próxima
    if "PORT" not in os.environ and is_port_in_use(PORT):
        for p in range(PORT + 1, PORT + 10):
            if not is_port_in_use(p):
                PORT = p
                break

    with ReusableTCPServer(("", PORT), CORSRequestHandler) as httpd:
        url = f"http://localhost:{PORT}"
        print(f"\n🚀 Servidor Ativo na porta: {PORT}")
        print(f"📁 Banco de Dados em: {ARQUIVO_DADOS}\n")

        # Abre o navegador apenas se estiver rodando na máquina local
        if "PORT" not in os.environ:
            try:
                webbrowser.open(url)
            except:
                pass

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Servidor parado.")
            httpd.shutdown()


if __name__ == "__main__":
    main()
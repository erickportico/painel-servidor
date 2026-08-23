"""
Servidor local para o Painel de Acompanhamento de Produção e Instalação
Resolve todos os problemas do protocolo file:// (CDN bloqueado, CORS, Tracking Prevention)

Uso:
  python servidor_painel.py           # Serve na porta 8000
  python servidor_painel.py 3000      # Serve na porta 3000

Depois abra no navegador: http://localhost:8000
"""

import http.server
import socketserver
import os
import sys
import webbrowser
import functools

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))


class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Servidor HTTP com CORS headers e MIME types corretos."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('directory', DIRECTORY)
        super().__init__(*args, **kwargs)

    def end_headers(self):
        # CORS headers - permite CDN scripts funcionarem
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        # Cache control - garante versão atualizada durante desenvolvimento
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        '.html': 'text/html; charset=utf-8',
        '.css': 'text/css; charset=utf-8',
        '.js': 'application/javascript; charset=utf-8',
        '.json': 'application/json; charset=utf-8',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
        '.ico': 'image/x-icon',
        '.pdf': 'application/pdf',
        '.woff': 'font/woff',
        '.woff2': 'font/woff2',
    }

    def log_message(self, format, *args):
        # Log mais limpo
        sys.stdout.write("[%s] %s\n" % (self.log_date_time_string(), format % args))


def is_port_in_use(port):
    """Verifica se a porta já está em uso."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def find_free_port(start_port, max_tries=10):
    """Encontra uma porta livre a partir de start_port."""
    for p in range(start_port, start_port + max_tries):
        if not is_port_in_use(p):
            return p
    return None


def main():
    global PORT

    # Verifica se a porta está livre
    if is_port_in_use(PORT):
        free = find_free_port(PORT + 1)
        if free:
            print(f"⚠️  Porta {PORT} já em uso, usando porta {free}")
            PORT = free
        else:
            print(f"❌ Portas {PORT}-{PORT+9} todas em uso. Feche algum servidor e tente novamente.")
            sys.exit(1)

    handler = CORSRequestHandler

    # Permite reutilizar a porta rapidamente
    socketserver.TCPServer.allow_reuse_address = True

    with socketserver.TCPServer(("", PORT), handler) as httpd:
        url = f"http://localhost:{PORT}"
        print("")
        print("╔══════════════════════════════════════════════════════════╗")
        print("║   PAINEL DE ACOMPANHAMENTO - Servidor Local             ║")
        print("╠══════════════════════════════════════════════════════════╣")
        print(f"║   Endereço: {url:<42s}   ║")
        dir_display = DIRECTORY[:42] if len(DIRECTORY) > 42 else DIRECTORY
        print(f"║   Pasta:    {dir_display:<42s}   ║")
        print("║                                                          ║")
        print("║   ✓ CORS habilitado                                     ║")
        print("║   ✓ CDN scripts liberados                               ║")
        print("║   ✓ PDF.js funcional                                    ║")
        print("║   ✓ localStorage sem bloqueio                           ║")
        print("║                                                          ║")
        print("║   Pressione Ctrl+C para parar o servidor                ║")
        print("╚══════════════════════════════════════════════════════════╝")
        print("")

        # Abre o navegador automaticamente
        try:
            webbrowser.open(url)
            print(f"🌐 Navegador aberto automaticamente: {url}")
        except:
            print(f"🌐 Abra manualmente no navegador: {url}")

        print("")
        print("Aguardando requisições... (Ctrl+C para parar)")
        print("─" * 58)

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n🛑 Servidor parado. Até logo!")
            httpd.shutdown()


if __name__ == "__main__":
    main()

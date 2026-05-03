import socket
import threading
from datetime import datetime
import os
import mimetypes
import time
import metrics_manager

# Configurações globais de rede
# '0.0.0.0' permite que o servidor aceite conexões de qualquer interface de rede (localhost, IP da rede local, etc.)
HOST = '0.0.0.0'
PORTA = 8080

# Experimento: Atraso Artificial
# Utilizado para testar como o cliente/navegador se comporta com latência e para validar as métricas de performance
SIMULATE_DELAY = 0 

def carregar_pagina_ou_arquivo(caminho_arquivo):
    """
    Função auxiliar para ler arquivos do sistema de arquivos e prepará-los para a resposta HTTP.
    Implementa uma lógica básica de tratamento de erros e descoberta de MIME type.
    """
    if not os.path.exists(caminho_arquivo):
        # RFC 7231: 404 Not Found é retornado quando o recurso não existe
        return "404 Not Found", b"<h1>404 - Arquivo nao encontrado</h1>", "text/html"
    
    # Identifica o tipo de conteúdo (ex: text/html, image/png) para o cabeçalho Content-Type
    mime_type, _ = mimetypes.guess_type(caminho_arquivo)
    if not mime_type: mime_type = "application/octet-stream" # Default para binários desconhecidos
    
    try:
        with open(caminho_arquivo, "rb") as f:
            return "200 OK", f.read(), mime_type
    except Exception as e:
        # Erro genérico do servidor caso falte permissão de leitura ou o arquivo esteja corrompido
        return "500 Internal Server Error", f"<h1>500 - Erro: {e}</h1>".encode(), "text/html"

def renderiza_dashboard(data_bin):
    """
    Motor de templates ultra-leve (Server-Side Rendering).
    Interpreta o HTML carregado e substitui placeholders {{...}} por métricas reais.
    """
    # Recupera o estado atualizado das métricas protegidas por lock
    tcp_stats = metrics_manager.get_full_stats()
    
    body = data_bin.decode('utf-8', errors='ignore')
    perf = tcp_stats["performance"]
    
    # Substituições de métricas escalares
    # Este padrão evita bibliotecas pesadas como Jinja2 para propósitos educacionais
    body = body.replace("{{total}}", str(tcp_stats["metrics"]["total_requests"]))
    body = body.replace("{{clients}}", str(tcp_stats["clients"]["total_unique"]))
    body = body.replace("{{last}}", str(tcp_stats["metrics"]["last_request"]))
    body = body.replace("{{active}}", str(tcp_stats["metrics"]["active_connections"]))
    body = body.replace("{{avg_time}}", f"{perf['avg_time_ms']:.2f}")
    body = body.replace("{{min_time}}", f"{perf['min_time_ms']:.2f}")
    body = body.replace("{{max_time}}", f"{perf['max_time_ms']:.2f}")
    body = body.replace("{{bytes}}", f"{tcp_stats['traffic']['total_bytes_sent'] / 1024:.2f} KB")
    body = body.replace("{{insights}}", metrics_manager.gerir_insights(tcp_stats))
    
    # Lógica de UI baseada em regras de negócio (Feedback visual de latência)
    status_color = "status-fast"
    if perf['avg_time_ms'] > 500: status_color = "status-slow"
    elif perf['avg_time_ms'] > 100: status_color = "status-medium"
    body = body.replace("{{perf_color}}", status_color)
    
    # Transformação de listas em fragmentos HTML (Lists para <li>)
    content_html = "".join([f"<li class='dash-list-item'>{item.upper()}: {valor}</li>" for item, valor in tcp_stats["content_types"].items()])
    body = body.replace("{{content_types}}", content_html)
    
    routes_html = "".join([f"<li class='dash-list-item'>{item.upper()}: {valor}</li>" for item, valor in tcp_stats["routes"].items()])
    body = body.replace("{{routes}}", routes_html)
    
    hist_html = "".join([f"<li class='dash-list-item'>{historico}</li>" for historico in tcp_stats["history"]])
    body = body.replace("{{history}}", hist_html)
    
    return body.encode()

def navegacao_cliente(client_socket, addr):
    """
    Worker principal: Processa o ciclo de vida de uma conexão TCP/HTTP.
    Executado em uma thread separada para não bloquear novas conexões (Concorrência).
    """
    start_time = time.perf_counter() # Alta precisão para medir latência
    try:
        # Recebe os daedos brutos do socket (Buffer de 1KB é suficiente para headers básicos)
        request = client_socket.recv(1024).decode()
        if not request: return

        # Parsing simplificado do protocolo HTTP (Protocol-level understanding)
        # Formato esperado: "GET /caminho HTTP/1.1"
        linha = request.split('\n')[0]
        partes = linha.split()
        if len(partes) < 2: return
        metodo, caminho = partes[0], partes[1].strip().rstrip('/')
        if not caminho: caminho = "/"

        # Aplicação de atraso sintético para testes de estresse e monitoramento
        if SIMULATE_DELAY > 0: time.sleep(SIMULATE_DELAY)

        # Roteador (Router) manual: Define para onde cada URL aponta
        status, data, content_type = "404 Not Found", "<h1>404 Página não encontrada</h1>".encode('utf-8'), "text/html"
        
        if caminho == "/":
            status, data, content_type = carregar_pagina_ou_arquivo("templates/index.html")
        elif caminho.startswith("/site"):
            # Permite servir arquivos estáticos de uma pasta específica
            rel_path = caminho.replace("/site", "").strip("/") or "index.html"
            status, data, content_type = carregar_pagina_ou_arquivo(os.path.join("site", rel_path))
        elif caminho in ["/dashboard", "/dashboard_tcp"]:
            # Rota especial que renderiza dados dinâmicos
            status, data, content_type = carregar_pagina_ou_arquivo("templates/dashboard_tcp.html")
            if status == "200 OK": data = renderiza_dashboard(data)
        elif caminho == "/arquivo.pdf":
            status, data, content_type = carregar_pagina_ou_arquivo("templates/arquivo.pdf")

        # Construção da Resposta HTTP (HTTP Response Packet)
        # Todo servidor web precisa enviar o Header seguido de uma linha vazia (\r\n\r\n) e o corpo (Payload)
        header = f"HTTP/1.1 {status}\r\nContent-Type: {content_type}\r\nContent-Length: {len(data)}\r\n\r\n"
        client_socket.send(header.encode() + data)

        # Telemetria e Observabilidade
        # Após o envio, calculamos métricas de performance para o Dashboard
        duration_ms = (time.perf_counter() - start_time) * 1000
        bytes_sent = len(header.encode() + data)
        active_threads = threading.active_count() - 1 # Subtraímos a thread principal (main loop)
        
        # Chamada atômica para atualizar o estado global de métricas
        metrics_manager.update_metrics(addr[0], metodo, caminho, content_type, duration_ms, bytes_sent, active_threads)

    except Exception as e:
        print(f"Erro no servidor ao processar {addr}: {e}")
    finally:
        # Crucial: Fechar o socket para liberar recursos do Sistema Operacional (File Descriptors)
        client_socket.close()

def inicia_servidor():
    """
    Configura o socket mestre, faz o bind e entra no loop de aceitação.
    """
    # AF_INET = IPv4 | SOCK_STREAM = TCP
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # SO_REUSEADDR permite reiniciar o servidor imediatamente sem esperar o timeout do kernel (TIME_WAIT)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind((HOST, PORTA))
        server.listen(10) # 'Backlog' de 10 conexões em fila antes de recusar novas
        print(f"Servidor Web TCP rodando em http://localhost:{PORTA}")
        
        while True:
            # Bloqueia a execução até que um cliente se conecte
            client_socket, addr = server.accept()
            
            # Delega o processamento para uma nova thread (Modelo Multi-threaded)
            # Isso permite que o servidor atenda múltiplos usuários simultaneamente
            threading.Thread(target=navegacao_cliente, args=(client_socket, addr)).start()
            
    except Exception as e:
        print(f"Falha crítica ao iniciar servidor: {e}")
    finally:
        server.close()

if __name__ == "__main__":
    try:
        inicia_servidor()
    except KeyboardInterrupt:
        # Garante que o usuário possa parar o servidor com Ctrl+C de forma limpa
        print("\nServidor encerrado pelo usuário (Ctrl+C).")


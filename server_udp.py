import socket

def run_udp_server():
    # Criamos o socket: AF_INET (IPv4) e SOCK_DGRAM (UDP)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # '0.0.0.0' significa que ele vai ouvir em todas as placas de rede do PC
    server_address = ('0.0.0.0', 8080)
    sock.bind(server_address)
    
    print(f"--- Servidor UDP Ativo ---")
    print(f"Ouvindo na porta: {server_address[1]}")
    print(f"Aguardando pacotes... (Pressione Ctrl+C para parar)")

    while True:
        # O servidor fica parado aqui até chegar algo
        data, address = sock.recvfrom(4096)
        
        print(f"\n[NOVO PACOTE] Origem: {address}")
        print(f"Conteúdo: {data.decode('utf-8', errors='ignore')}")
        
        # Envia uma resposta de confirmação para quem mandou
        resposta = "Mensagem recebida pelo servidor!".encode('utf-8')
        sock.sendto(resposta, address)

if __name__ == "__main__":
    run_udp_server()    
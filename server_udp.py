import socket

def run_server():
    # AF_INET = IPv4, SOCK_DGRAM = UDP
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Ouvindo em todas as interfaces na porta 8080
    server_address = ('0.0.0.0', 8080)
    server_socket.bind(server_address)
    
    print(f"--- Servidor de Ping UDP Ativo na porta {server_address[1]} ---")

    while True:
        # Recebe a mensagem do cliente
        data, address = server_socket.recvfrom(4096)
        message = data.decode().upper()
        
        # Se recebeu 'PING', responde 'PONG'
        if "PING" in message:
            response = "PONG"
            server_socket.sendto(response.encode(), address)
            print(f"Recebido: {message} de {address} -> Respondido: {response}")

if __name__ == "__main__":
    run_server()
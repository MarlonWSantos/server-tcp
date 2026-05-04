import socket
import time

def run_ping_client():
    server_address = ('127.0.0.1', 8080)
    total_pings = 10
    timeout = 1.0  # 1 segundo de espera
    
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(timeout)
    
    rtts = []
    lost_packets = 0

    print(f"Iniciando Ping UDP em {server_address[0]}:{server_address[1]}...\n")

    for i in range(1, total_pings + 1):
        start_time = time.time()
        message = f"PING {i}"
        
        try:
            # Envia o Ping
            client_socket.sendto(message.encode(), server_address)
            
            # Tenta receber o Pong
            data, server = client_socket.recvfrom(4096)
            end_time = time.time()
            
            # Calcula o RTT em milissegundos
            rtt = (end_time - start_time) * 1000
            rtts.append(rtt)
            
            print(f"Resposta de {server}: {data.decode()} | seq={i} | RTT={rtt:.2f} ms")
            
        except socket.timeout:
            lost_packets += 1
            print(f"Solicitação seq={i}: Esgotado o tempo limite (Timeout)")
        
        # Pequena pausa para não inundar a rede instantaneamente
        time.sleep(0.1)

    # --- Estatísticas finais ---
    print("\n--- Estatísticas do Ping ---")
    loss_percent = (lost_packets / total_pings) * 100
    print(f"Pacotes: Enviados = {total_pings}, Recebidos = {len(rtts)}, Perdidos = {lost_packets} ({loss_percent:.1f}% de perda)")
    
    if rtts:
        print(f"RTT: Mínimo = {min(rtts):.2f}ms | Máximo = {max(rtts):.2f}ms | Média = {sum(rtts)/len(rtts):.2f}ms")

    client_socket.close()

if __name__ == "__main__":
    run_ping_client()
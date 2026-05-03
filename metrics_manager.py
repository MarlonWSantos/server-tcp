import threading
from datetime import datetime

# Estrutura de Dados Global (In-Memory State)
# Como o servidor é multi-threaded, este objeto é acessado simultaneamente por várias threads.
stats = {
    "metrics": {
        "total_requests": 0,
        "last_request": "N/A",
        "active_connections": 0
    },
    "performance": {
        "avg_time_ms": 0,
        "min_time_ms": 0,
        "max_time_ms": 0,
        "total_time_ms": 0,
        "response_count": 0
    },
    "clients": {
        "unique_ips": set(), # Sets garantem unicidade automaticamente
        "ip_counts": {},
        "top_ip": "N/A"
    },
    "content_types": {
        "html": 0, "css": 0, "pdf": 0, "others": 0
    },
    "routes": {},
    "history": [], # LIFO (Last In, First Out) simulado para o log de atividades
    "traffic": {
        "total_bytes_sent": 0
    }
}

# Primitive de Sincronização (Mutex)
# Essencial para evitar 'Race Conditions'. Garante que apenas uma thread altere o dicionário 'stats' por vez.
stats_lock = threading.Lock()


def gerir_insights(metrics_data):
    """
    Business Logic Layer: Transforma números brutos em informações úteis (Insights).
    Exemplo de monitoramento proativo.
    """
    if not metrics_data: return "Aguardando dados..."
    perf = metrics_data["performance"]
    insights = []
    
    # Heurística simples de performance
    if perf["avg_time_ms"] > 500:
        insights.append("Tempo de resposta alto. Verifique a carga do servidor.")
    elif perf["avg_time_ms"] > 0:
        insights.append("Servidor estável.")
        
    insights.append("TCP garante entrega confiável vs UDP.")
    return " | ".join(insights)

def update_metrics(ip_cliente, metodo, caminho, content_type, duration_ms, bytes_sent, active_threads):
    """
    Ponto de entrada para atualização de telemetria.
    Thread-safe: utiliza o Lock para proteger a integridade dos dados.
    """
    with stats_lock:
        # Atualização de métricas básicas
        stats["metrics"]["active_connections"] = active_threads
        stats["metrics"]["total_requests"] += 1
        stats["metrics"]["last_request"] = f"{metodo} {caminho}"
        
        # Histórico circular (mantém apenas os últimos 10 eventos)
        stats["history"].insert(0, f"{datetime.now().strftime('%H:%M:%S')} - {metodo} {caminho}")
        stats["history"] = stats["history"][:10]
        
        # Gestão de Clientes e IPs
        stats["clients"]["unique_ips"].add(ip_cliente)
        stats["clients"]["ip_counts"][ip_cliente] = stats["clients"]["ip_counts"].get(ip_cliente, 0) + 1
        # Cálculo de Top IP (Frequência)
        stats["clients"]["top_ip"] = max(stats["clients"]["ip_counts"], key=stats["clients"]["ip_counts"].get)
        
        # Filtro de Rotas: Apenas páginas HTML entram no ranking de rotas (Page Views)
        # Ignora arquivos estáticos (CSS, imagens) para não poluir o dashboard
        if "text/html" in content_type:
            stats["routes"][caminho] = stats["routes"].get(caminho, 0) + 1
            
        stats["traffic"]["total_bytes_sent"] += bytes_sent
        
        # Categorização por Content-Type
        if "html" in content_type: stats["content_types"]["html"] += 1
        elif "css" in content_type: stats["content_types"]["css"] += 1
        elif "pdf" in content_type: stats["content_types"]["pdf"] += 1
        else: stats["content_types"]["others"] += 1
        
        # Cálculos de Performance (Média Móvel e Extremos)
        perf = stats["performance"]
        perf["response_count"] += 1
        perf["total_time_ms"] += duration_ms
        perf["avg_time_ms"] = perf["total_time_ms"] / perf["response_count"]
        
        # Atualiza Min/Max
        if perf["response_count"] == 1:
            perf["min_time_ms"] = duration_ms
            perf["max_time_ms"] = duration_ms
        else:
            perf["min_time_ms"] = min(perf["min_time_ms"], duration_ms)
            perf["max_time_ms"] = max(perf["max_time_ms"], duration_ms)
            
            
    # As métricas são mantidas apenas em memória RAM durante esta execução.
    pass

def get_full_stats():
    """
    Interface de Leitura para o Dashboard.
    Retorna uma cópia profunda (snapshot) dos dados para evitar que o motor de templates
    tente ler algo enquanto outra thread está escrevendo (RuntimeError: dictionary changed size).
    """
    with stats_lock:
        return {
            "metrics": {
                "total_requests": stats["metrics"]["total_requests"],
                "last_request": stats["metrics"]["last_request"],
                "active_connections": stats["metrics"]["active_connections"]
            },
            "performance": stats["performance"].copy(),
            "clients": {
                "total_unique": len(stats["clients"]["unique_ips"]),
                "top_ip": stats["clients"]["top_ip"]
            },
            "content_types": stats["content_types"].copy(),
            "routes": stats["routes"].copy(),
            "history": list(stats["history"]),
            "traffic": stats["traffic"].copy()
        }


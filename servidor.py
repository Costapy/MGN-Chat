import socket
import threading

mensagens = {}

def handle_client(conn, addr):
    print(f"Nova conexão de {addr}")
    
    while True:
        try:
            dados = conn.recv(1024).decode()
            if not dados:
                break
            
            partes = dados.split('|') #SEND|DESTINATARIO|msg
            if partes[0] == "SEND":
                destinatario, mensagem = partes[1], partes[2]
                if destinatario not in mensagens:
                    mensagens[destinatario] = []
                mensagens[destinatario].append(f"{addr[0]}: {mensagem}")
                conn.send("Mensagem enviada!".encode())

            elif partes[0] == "RECEIVE":#SEND|REMETENTE|MSG
                remetente = partes[1]
                if remetente in mensagens and mensagens[remetente]:
                    resposta = "\n".join(mensagens.pop(remetente))
                else:
                    resposta = "Nenhuma mensagem."
                conn.send(resposta.encode())

        except ConnectionResetError:
            break

    conn.close()
    print(f"Conexão encerrada com {addr}")

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", 5000))
    server.listen(5)
    print("Servidor rodando na porta 5000...")

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()

start_server()

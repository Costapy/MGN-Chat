import socket
import threading

def receber_mensagens(client, nome_usuario):
    """Thread para receber mensagens do servidor continuamente."""
    while True:
        try:
            client.send(f"RECEIVE|{nome_usuario}".encode())
            resposta = client.recv(1024).decode()
            if resposta != "Nenhuma mensagem.":
                print(f"\n📩 Nova mensagem:\n{resposta}\n")
        except:
            print("Erro ao receber mensagens.")
            break

def iniciar_cliente():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(("127.0.0.1", 5000))

    nome_usuario = input("Digite seu nome de usuário: ")

    # Inicia uma thread para receber mensagens continuamente
    thread_recebimento = threading.Thread(target=receber_mensagens, args=(client, nome_usuario), daemon=True)
    thread_recebimento.start()

    print("🟢 Conectado! Envie mensagens digitando 'destinatario|mensagem' ou 'sair' para encerrar.")
    
    while True:
        entrada = input("> ")
        if entrada.lower() == "sair":
            break

        try:
            destinatario, mensagem = entrada.split('|', 1)
            client.send(f"SEND|{destinatario}|{mensagem}".encode())
            resposta = client.recv(1024).decode()
            print(f"✅ {resposta}")
        except ValueError:
            print("Formato inválido! Use: destinatario|mensagem")

    client.close()

iniciar_cliente()

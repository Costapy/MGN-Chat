import zmq
import time
import json
import os
from collections import defaultdict
from threading import Thread

USER_DATA_FILE = "user_data.json"

def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_user_data(user_data):
    with open(USER_DATA_FILE, "w") as f:
        json.dump(user_data, f)
class ChatServer:
    def __init__(self):
        self.context = zmq.Context()

        self.receiver = self.context.socket(zmq.REP)
        self.receiver.bind("tcp://*:5555")

        self.notifier = self.context.socket(zmq.PUB)
        self.notifier.bind("tcp://*:5556")

        self.messages = defaultdict(list)
        self.active_users = set()

    def handle_messages(self):
        # Carrega os dados de usuário ao iniciar o servidor
        self.user_data = load_user_data()

        while True:
            try:
                msg = self.receiver.recv_json()
                print(f"Servidor recebeu: {msg}")

                if msg['type'] == 'connect':
                    ip = msg.get('ip')
                    if ip in self.user_data:
                        user = self.user_data[ip]
                        print(f"Usuário reconhecido: {user} para o IP {ip}")
                    else:
                        user = msg.get('user')
                        if user:
                            self.user_data[ip] = user
                            save_user_data(self.user_data)
                            print(f"Novo usuário registrado: {user} para o IP {ip}")
                        else:
                            # Caso o nome não tenha sido enviado, envia um erro
                            self.receiver.send_json({'status': 'error', 'message': 'Nome não fornecido'})
                            continue

                    self.active_users.add(user)
                    self.receiver.send_json({'status': 'connected', 'user': user})

                # Tratamento de outros tipos de mensagem...
                elif msg['type'] == 'message':
                    recipient = msg.get('to')
                    if recipient:
                        # Armazena a mensagem para o destinatário
                        self.messages[recipient].append(msg)
                        # Envia uma resposta para confirmar que a mensagem foi recebida
                        self.receiver.send_json({'status': 'message sent'})

                elif msg['type'] == 'request_users_online':
                    self.receiver.send_json({'users': list(self.active_users)})
                elif msg['type'] == 'fetch':
                    user = msg['user']
                    user_messages = self.messages.get(user, [])
                    self.receiver.send_json({'messages': user_messages})
                    self.messages[user] = []
                elif msg['type'] == 'disconnect':
                    user = msg['user']
                    if user in self.active_users:
                        self.active_users.remove(user)
                    self.receiver.send_json({'status': 'disconnected'})
            except Exception as e:
                print(f"Erro no servidor: {e}")


    def run(self):
        print("Servidor de chat iniciado...")
        Thread(target=self.handle_messages, daemon=True).start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nDesligando servidor...")
            self.receiver.close()
            self.notifier.close()
            self.context.term()


if __name__ == "__main__":
    server = ChatServer()
    server.run()

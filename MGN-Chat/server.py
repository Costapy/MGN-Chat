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
        # Novo dicionário para grupos
        self.groups = {}  # Ex: {"grupo1": ["Marcos", "NATHAN"]}

    def handle_messages(self):
        self.user_data = load_user_data()
        while True:
            try:
                msg = self.receiver.recv_json()
                print(f"Servidor recebeu: {msg}")
                
                msg_type = msg.get('type')
                if msg_type == 'connect':
                    # (Fluxo de conexão existente)
                    ip = msg.get('ip')
                    if ip in self.user_data:
                        user = self.user_data[ip]
                    else:
                        user = msg.get('user')
                        if user:
                            self.user_data[ip] = user
                            save_user_data(self.user_data)
                        else:
                            self.receiver.send_json({'status': 'error', 'message': 'Nome n\u00e3o fornecido'})
                            continue
                    self.active_users.add(user)
                    self.receiver.send_json({'status': 'connected', 'user': user})

                elif msg_type == 'create_group':
                    group_id = msg.get('group_id')
                    members = msg.get('members', [])
                    if group_id and members:
                        self.groups[group_id] = members
                        self.receiver.send_json({'status': 'group created', 'group_id': group_id})
                    else:
                        self.receiver.send_json({'status': 'error', 'message': 'Dados insuficientes para criar grupo'})

                elif msg_type == 'join_group':
                    group_id = msg.get('group_id')
                    user = msg.get('user')
                    if group_id in self.groups:
                        self.groups[group_id].append(user)
                        self.receiver.send_json({'status': 'joined', 'group_id': group_id})
                    else:
                        self.receiver.send_json({'status': 'error', 'message': 'Grupo n\u00e3o existe'})

                elif msg_type == 'group_message':
                    group_id = msg.get('group')
                    sender = msg.get('from')
                    message_text = msg.get('message')
                    if group_id in self.groups:
                        # Para cada membro do grupo (exceto o remetente), armazena a mensagem
                        for member in self.groups[group_id]:
                            if member != sender:
                                # Você pode armazenar como mensagem de grupo (adicione o campo 'group')
                                self.messages[member].append({
                                    'from': sender,
                                    'group': group_id,
                                    'message': message_text
                                })
                        self.receiver.send_json({'status': 'message sent to group'})
                    else:
                        self.receiver.send_json({'status': 'error', 'message': 'Grupo n\u00e3o encontrado'})

                elif msg_type == 'message':
                    # Mensagens individuais (como antes)
                    recipient = msg.get('to')
                    if recipient:
                        self.messages[recipient].append(msg)
                        self.receiver.send_json({'status': 'message sent'})
                
                elif msg_type == 'request_users_online':
                    self.receiver.send_json({'users': list(self.active_users)})
                elif msg_type == 'fetch':
                    user = msg['user']
                    user_messages = self.messages.get(user, [])
                    self.receiver.send_json({'messages': user_messages})
                    self.messages[user] = []
                elif msg_type == 'disconnect':
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

import zmq
import time
from collections import defaultdict
from threading import Thread
from db import Session, Message


class ChatServer:
    def __init__(self):
        self.context = zmq.Context()

        self.receiver = self.context.socket(zmq.REP)
        self.receiver.bind("tcp://*:5555")

        self.notifier = self.context.socket(zmq.PUB)
        self.notifier.bind("tcp://*:5556")

        self.active_users = set()

    def handle_messages(self):
        while True:
            try:
                msg = self.receiver.recv_json()
                print(f"Servidor recebeu: {msg}")

                session = Session()  # Criar uma sessão para interagir com o banco

                if msg['type'] == 'connect':
                    user = msg['user']
                    self.active_users.add(user)
                    self.receiver.send_json({'status': 'connected'})

                    # Buscar mensagens pendentes no banco
                    messages = Message.get_messages_for_user(session, user)
                    if messages:
                        self.receiver.send_json({'status': 'connected', 'pending_messages': messages})
                    else:
                        self.receiver.send_json({'status': 'connected'})

                elif msg['type'] == 'message':
                    sender = msg['from']
                    recipient = msg['to']
                    message = msg['message']

                    # Salvar no banco
                    Message.save_message(session, sender, recipient, message)

                    self.receiver.send_json({'status': 'delivered'})
                    self.notifier.send_string(recipient)

                elif msg['type'] == 'request_users_online':
                    self.receiver.send_json({'users': list(self.active_users)})

                elif msg['type'] == 'fetch':
                    user = msg['user']
                    user_messages = Message.get_messages_for_user(session, user)
                    self.receiver.send_json({'messages': user_messages})

                elif msg['type'] == 'disconnect':
                    user = msg['user']
                    if user in self.active_users:
                        self.active_users.remove(user)
                    self.receiver.send_json({'status': 'disconnected'})

                session.close()  # Fechar a sessão após cada operação

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

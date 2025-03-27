import zmq
import time
from threading import Thread
import json

class ChatClient:
    def __init__(self, user_id):
        self.user_id = user_id
        self.context = zmq.Context()
        self.running = True
        
        # Socket para enviar mensagens ao servidor
        self.sender = self.context.socket(zmq.REQ)
        self.sender.connect("tcp://localhost:5555")
        
        # Socket para receber notificações
        self.notifier = self.context.socket(zmq.SUB)
        self.notifier.connect("tcp://localhost:5556")
        self.notifier.setsockopt_string(zmq.SUBSCRIBE, self.user_id)
        
        # Conecta ao servidor
        self._send_to_server({'type': 'connect', 'user': self.user_id})
        
    def _send_to_server(self, message):
        self.sender.send_json(message)
        return self.sender.recv_json()
    
    def send_message(self, recipient, message):
        msg = {
            'type': 'message',
            'from': self.user_id,
            'to': recipient,
            'message': message
        }
        return self._send_to_server(msg)
    
    def fetch_messages(self):
        response = self._send_to_server({
            'type': 'fetch',
            'user': self.user_id
        })
        return response.get('messages', [])
    
    def listen_for_messages(self):
        while self.running:
            try:
                notification = self.notifier.recv_string(flags=zmq.NOBLOCK)
                if notification == self.user_id:
                    messages = self.fetch_messages()
                    for msg in messages:
                        print(f"\n[{msg['from']}]: {msg['message']}")
                        print(f"Você: ", end="", flush=True)
            except zmq.Again:
                pass
            time.sleep(0.1)
    
    def start_chat(self, recipient):
        print(f"\nIniciando chat com {recipient} (Digite 'sair' para terminar)")

        Thread(target=self.listen_for_messages, daemon=True).start()
        
        try:
            while self.running:
                message = input("Você: ")
                
                if message.lower() == 'sair':
                    break

                self.send_message(recipient, message)
                
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            self._send_to_server({
                'type': 'disconnect',
                'user': self.user_id
            })
            self.sender.close()
            self.notifier.close()
            self.context.term()

if __name__ == "__main__":
    user_id = input("Digite seu nome de usuário: ")
    client = ChatClient(user_id)
    
    recipient = input("Digite o nome do usuário com quem deseja conversar: ")
    client.start_chat(recipient)
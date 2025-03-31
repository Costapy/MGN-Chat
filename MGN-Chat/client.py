from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from threading import Thread
import time
import zmq

SERVER_IP = "192.168.1.10"
class ChatClient:
    def __init__(self, user_id):
        self.user_id = user_id
        self.context = zmq.Context()
        self.running = True
        # Socket para enviar mensagens ao servidor
        self.sender = self.context.socket(zmq.REQ)
        self.sender.connect(f"tcp://{SERVER_IP}:5555")

        # Socket para receber notificações
        self.notifier = self.context.socket(zmq.SUB)
        self.notifier.connect(f"tcp://{SERVER_IP}:5556")
        self.notifier.setsockopt_string(zmq.SUBSCRIBE, self.user_id)

        # Conecta ao servidor
        self._send_to_server({'type': 'connect', 'user': self.user_id})

    def _send_to_server(self, message):
        try:
            self.sender.send_json(message)
            if self.sender.poll(2000):  # Espera no máximo 2 segundos
                return self.sender.recv_json()
            else:
                print("Timeout ao aguardar resposta do servidor")
                return {}
        except Exception as e:
            print(f"Erro ao enviar mensagem: {e}")
            return {}

    def send_message(self, recipient, message):
        msg = {
            'type': 'message',
            'from': self.user_id,
            'to': recipient,
            'message': message
        }
        return self._send_to_server(msg)

    def fetch_messages(self):
        response = self._send_to_server({'type': 'fetch', 'user': self.user_id})
        return response.get('messages', [])

    def request_users_online(self):
        response = self._send_to_server({"type": "request_users_online"})
        return response.get('users', [])


class ChatApp(App):
    def __init__(self, user_id, **kwargs):
        super().__init__(**kwargs)
        self.client = ChatClient(user_id)
        self.user_id = user_id
        self.recipient = None

    def build(self):
        self.layout = BoxLayout(orientation='vertical')

        # Área de mensagens
        self.scroll_view = ScrollView(size_hint=(1, 0.6))
        self.chat_label = Label(text='', size_hint_y=None, valign='top', halign='left')
        self.chat_label.bind(size=self.update_chat_scroll)
        self.scroll_view.add_widget(self.chat_label)
        self.layout.add_widget(self.scroll_view)

        # Entrada de mensagem
        self.text_input = TextInput(size_hint=(1, 0.1), multiline=False)
        self.layout.add_widget(self.text_input)

        # Botão de envio
        self.send_button = Button(text='Enviar', size_hint=(1, 0.1))
        self.send_button.bind(on_press=self.send_message)
        self.layout.add_widget(self.send_button)

        # Lista de usuários online
        self.user_list_label = Label(text='Usuários Online:', size_hint=(1, 0.05))
        self.layout.add_widget(self.user_list_label)

        self.user_list_box = BoxLayout(orientation='vertical', size_hint=(1, 0.15))
        self.layout.add_widget(self.user_list_box)

        self.update_users_online()
        Thread(target=self.start_receiving_messages, daemon=True).start()

        Clock.schedule_interval(self.fetch_and_update_chat, 1)  # Atualiza mensagens a cada 1 segundo
        Clock.schedule_interval(self.update_users_online, 5)    # Atualiza usuários a cada 5 segundos

        return self.layout

    def update_chat_scroll(self, instance, value):
        instance.text_size = (instance.width, None)
        instance.height = instance.texture_size[1]
        self.scroll_view.scroll_y = 0  # Garante que o chat role para a última mensagem

    def send_message(self, instance):
        if not self.recipient:
            self.chat_label.text += "\n[Erro] Selecione um usuário para conversar!"
            return
        message = self.text_input.text
        if message:
            self.client.send_message(self.recipient, message)
            self.chat_label.text += f"\nVocê para {self.recipient}: {message}"
            self.text_input.text = ''

    def start_receiving_messages(self):
        while True:
            self.fetch_and_update_chat(0)
            time.sleep(1)

    def fetch_and_update_chat(self, dt):
        messages = self.client.fetch_messages()
        for msg in messages:
            self.update_chat(msg)

    def update_chat(self, msg):
        self.chat_label.text += f"\n{msg['from']}: {msg['message']}"

    def update_users_online(self, dt=None):
        users = self.client.request_users_online()
        
        # Atualiza o rótulo da lista de usuários
        self.user_list_label.text = f'Usuários Online: ({len(users)})'

        # Limpa a lista antes de recriar os botões
        self.user_list_box.clear_widgets()

        for user in users:
            if user != self.user_id:  # Não exibir o próprio usuário
                btn = Button(text=user, size_hint_y=None, height=40)
                btn.bind(on_press=self.select_user)
                self.user_list_box.add_widget(btn)

    def select_user(self, instance):
        """ Define o usuário selecionado para conversar """
        self.recipient = instance.text
        self.chat_label.text += f"\n[Agora conversando com {self.recipient}]"


if __name__ == '__main__':
    user_id = input("Digite seu nome de usuário: ")
    ChatApp(user_id).run()

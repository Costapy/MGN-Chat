import socket
import time
import zmq
from threading import Thread
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.textinput import TextInput
from kivy.storage.jsonstore import JsonStore

store = JsonStore('user_store.json')

# Endereço do servidor
SERVER_IP = "18.221.96.181"

def get_local_ip():
    "Obtém o IP local do cliente."
    return socket.gethostbyname(socket.gethostname())

# ---------------------------------------------------------
# Cliente de Chat com ZMQ
# ---------------------------------------------------------
class ChatClient:
    def __init__(self, user_id):
        self.user_id = user_id
        self.context = zmq.Context()

        # Socket para enviar requisições ao servidor
        self.sender = self.context.socket(zmq.REQ)
        self.sender.connect(f"tcp://{SERVER_IP}:5555")

        # Socket para receber notificações
        self.notifier = self.context.socket(zmq.SUB)
        self.notifier.connect(f"tcp://{SERVER_IP}:5556")
        self.notifier.setsockopt_string(zmq.SUBSCRIBE, self.user_id)

        # Obtém o IP e envia o pedido de conexão com o nome
        self.ip = get_local_ip()
        connect_msg = {'type': 'connect', 'ip': self.ip, 'user': self.user_id}
        response = self._send_to_server(connect_msg)
        # Se o servidor reconhecer o IP, pode atualizar o nome
        if response.get('status') == 'connected' and 'user' in response:
            self.user_id = response['user']

    def _send_to_server(self, message):
        try:
            self.sender.send_json(message)
            if self.sender.poll(2000):  # espera até 2 segundos por uma resposta
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

# ---------------------------------------------------------
# Tela de Login
# ---------------------------------------------------------
class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super(LoginScreen, self).__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        self.info_label = Label(text="Entre com seu nome:", font_size=20)
        self.name_input = TextInput(multiline=False, font_size=18)
        self.login_button = Button(text="Entrar", size_hint=(1, 0.3), font_size=20)
        self.login_button.bind(on_press=self.login)
        layout.add_widget(self.info_label)
        layout.add_widget(self.name_input)
        layout.add_widget(self.login_button)
        self.add_widget(layout)

    def kill(self):
        # Obtém a tela 'profile' a partir do ScreenManager
        profile_screen = self.root.get_screen('profile')
        # Acessa os IDs que estão definidos na tela 'profile'
        enname = profile_screen.ids.user.text
        epass = profile_screen.ids.password.text
        eid = profile_screen.ids.ID.text
        # Valores esperados para autenticação
        name = "pranav"
        password = "1234"
        id = '1'
    
        if name == enname and password == epass and id == eid:
            profile_screen.ids.error.text = 'Youre logged in'
            profile_screen.ids.user.text = ''
            profile_screen.ids.password.text = ''
            profile_screen.ids.ID.text = ''
        else:
            profile_screen.ids.error.text = 'Please enter Valid credentials'
            profile_screen.ids.user.text = ''
            profile_screen.ids.password.text = ''
            profile_screen.ids.ID.text = ''
    

    def login(self, instance):
        user_name = self.name_input.text.strip()
        if user_name:
            # Cria a instância do ChatClient e guarda no ScreenManager
            self.manager.chat_client = ChatClient(user_id=user_name)
            # Salva o nome do usuário localmente
            store.put('user', name=user_name)
            # Muda para a tela de chat
            self.manager.current = 'chat'
        else:
            self.info_label.text = "Por favor, digite um nome válido."


# ---------------------------------------------------------
# Tela de Chat
# ---------------------------------------------------------
class ChatScreen(Screen):
    def __init__(self, **kwargs):
        super(ChatScreen, self).__init__(**kwargs)
        self.recipient = None
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        # Configuração do layout (chat_label, msg_box, users_label, etc.)
        self.chat_label = Label(text="", size_hint_y=None, font_size=16)
        self.chat_label.bind(texture_size=self._update_chat_height)
        chat_box = BoxLayout(orientation='vertical', size_hint=(1, 0.6))
        chat_box.add_widget(self.chat_label)
        layout.add_widget(chat_box)

        msg_box = BoxLayout(size_hint=(1, 0.1))
        self.message_input = TextInput(multiline=False, font_size=16)
        send_button = Button(text="Enviar", size_hint=(0.3, 1), font_size=16)
        send_button.bind(on_press=self.send_message)
        msg_box.add_widget(self.message_input)
        msg_box.add_widget(send_button)
        layout.add_widget(msg_box)

        self.users_label = Label(text="Usuários Online: (0)", size_hint=(1, 0.1), font_size=16)
        layout.add_widget(self.users_label)
        self.users_box = BoxLayout(orientation='vertical', size_hint=(1, 0.2))
        layout.add_widget(self.users_box)

        self.add_widget(layout)

        # Atualiza mensagens e usuários periodicamente
        Clock.schedule_interval(self.fetch_messages, 1)
        Clock.schedule_interval(self.update_users_online, 5)


    def _update_chat_height(self, instance, value):
        instance.height = instance.texture_size[1]

    def send_message(self, instance):
        if not self.recipient:
            self.chat_label.text += "\n[Erro] Selecione um usuário para conversar!"
            return
        message = self.message_input.text.strip()
        if message:
            self.manager.chat_client.send_message(self.recipient, message)
            self.chat_label.text += f"\nVocê para {self.recipient}: {message}"
            self.message_input.text = ''

    def fetch_messages(self, dt):
        if not hasattr(self.manager, 'chat_client') or self.manager.chat_client is None:
            return
        messages = self.manager.chat_client.fetch_messages()
        for msg in messages:
            self.chat_label.text += f"\n{msg['from']}: {msg['message']}"

    def update_users_online(self, dt):
        if not hasattr(self.manager, 'chat_client') or self.manager.chat_client is None:
            return
        users = self.manager.chat_client.request_users_online()
        self.users_label.text = f"Usuários Online: ({len(users)})"
        self.users_box.clear_widgets()
        for user in users:
            if user != self.manager.chat_client.user_id:
                btn = Button(text=user, size_hint_y=None, height=40, font_size=16)
                btn.bind(on_press=self.select_user)
                self.users_box.add_widget(btn)

    
    def select_user(self, instance):
        self.recipient = instance.text
        self.chat_label.text += f"\n[Agora conversando com {self.recipient}]"


# ---------------------------------------------------------
# Gerenciador de Telas e App
# ---------------------------------------------------------
class ChatApp(App):
    def build(self):
        sm = ScreenManager()
        sm.chat_client = None
        login_screen = LoginScreen(name='login')
        chat_screen = ChatScreen(name='chat')
        sm.add_widget(login_screen)
        sm.add_widget(chat_screen)
        
        # Verifica se o usuário já está salvo localmente
        store = JsonStore('user_store.json')
        if store.exists('user'):
            user_name = store.get('user')['name']
            sm.chat_client = ChatClient(user_id=user_name)
            sm.current = 'chat'
        else:
            sm.current = 'login'
        return sm


if __name__ == '__main__':
    ChatApp().run()

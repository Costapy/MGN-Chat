import socket
import time
import zmq
from threading import Thread
from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.storage.jsonstore import JsonStore
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.button import Button

store = JsonStore('user_store.json')
SERVER_IP = "18.221.96.181"

def get_local_ip():
    return socket.gethostbyname(socket.gethostname())

# --------------------------------------------------
# Cliente de Chat com ZeroMQ
# --------------------------------------------------
class ChatClient:
    def __init__(self, user_id):
        self.user_id = user_id
        self.context = zmq.Context()
        self.sender = self.context.socket(zmq.REQ)
        self.sender.connect(f"tcp://{SERVER_IP}:5555")
        self.notifier = self.context.socket(zmq.SUB)
        self.notifier.connect(f"tcp://{SERVER_IP}:5556")
        self.notifier.setsockopt_string(zmq.SUBSCRIBE, self.user_id)
        self.ip = get_local_ip()
        connect_msg = {'type': 'connect', 'ip': self.ip, 'user': self.user_id}
        response = self._send_to_server(connect_msg)
        if response.get('status') == 'connected' and 'user' in response:
            self.user_id = response['user']

    def _send_to_server(self, message):
        try:
            self.sender.send_json(message)
            if self.sender.poll(2000):
                return self.sender.recv_json()
            else:
                print("Timeout ao aguardar resposta do servidor")
                return {}
        except Exception as e:
            print(f"Erro ao enviar mensagem: {e}")
            return {}

    def send_message(self, recipient, message, group=False):
        msg_type = 'group_message' if group else 'message'
        msg = {
            'type': msg_type,
            'from': self.user_id,
            'message': message
        }
        if group:
            msg['group'] = recipient
        else:
            msg['to'] = recipient
        return self._send_to_server(msg)

    def fetch_messages(self):
        response = self._send_to_server({'type': 'fetch', 'user': self.user_id})
        return response.get('messages', [])

    def request_users_online(self):
        response = self._send_to_server({"type": "request_users_online"})
        return response.get('users', [])

    def create_group(self, group_id, members):
        msg = {
            'type': 'create_group',
            'group_id': group_id,
            'members': members
        }
        return self._send_to_server(msg)

# --------------------------------------------------
# Interface com Kivy (KV string)
# --------------------------------------------------
kv = """
ScreenManager:
    LoginScreen:
    MainMenuScreen:
    UserListScreen:
    CreateGroupScreen:
    ChatScreen:

<LoginScreen>:
    name: "login"
    BoxLayout:
        orientation: 'vertical'
        padding: 20
        spacing: 20
        Label:
            text: "Entre com seu nome:"
            font_size: 20
        TextInput:
            id: name_input
            multiline: False
            font_size: 18
        Button:
            text: "Entrar"
            size_hint_y: 0.3
            on_press: root.do_login()

<MainMenuScreen>:
    name: "menu"
    BoxLayout:
        orientation: 'vertical'
        padding: 20
        spacing: 20
        Label:
            text: "Bem-vindo! Escolha uma op\u00e7\u00e3o:"
            font_size: 20
        Button:
            text: "Chat Individual"
            size_hint_y: 0.3
            on_press: root.go_to_individual()
        Button:
            text: "Criar Grupo"
            size_hint_y: 0.3
            on_press: root.go_to_create_group()

<UserListScreen>:
    name: "user_list"
    BoxLayout:
        orientation: 'vertical'
        padding: 20
        spacing: 20
        Label:
            text: "Selecione um usu\u00e1rio para conversar:"
            font_size: 20
        BoxLayout:
            id: users_box
            orientation: 'vertical'
        Button:
            text: "Voltar ao Menu"
            size_hint_y: 0.2
            on_press: app.root.current = "menu"

<CreateGroupScreen>:
    name: "create_group"
    BoxLayout:
        orientation: 'vertical'
        padding: 20
        spacing: 20
        Label:
            text: "Selecione os usu\u00e1rios online para criar o grupo:"
            font_size: 20
        BoxLayout:
            id: group_users_box
            orientation: 'vertical'
        Button:
            text: "Criar Grupo"
            size_hint_y: 0.2
            on_press: root.create_group_action()
        Button:
            text: "Voltar ao Menu"
            size_hint_y: 0.2
            on_press: app.root.current = "menu"

<ChatScreen>:
    name: "chat"
    BoxLayout:
        orientation: 'vertical'
        padding: 10
        spacing: 10
        ScrollView:
            do_scroll_x: False
            Label:
                id: chat_label
                text: ""
                font_size: 16
                size_hint_y: None
                height: self.texture_size[1]
                markup: True
        BoxLayout:
            size_hint_y: 0.1
            TextInput:
                id: message_input
                multiline: False
                font_size: 16
            Button:
                text: "Enviar"
                size_hint_x: 0.3
                on_press: root.send_message()
        Label:
            id: current_chat_label
            text: "Conversa Individual"
            font_size: 16
        Button:
            text: "Voltar ao Menu"
            size_hint_y: 0.2
            on_press: app.root.current = "menu"
"""

# --------------------------------------------------
# Telas do App
# --------------------------------------------------
class LoginScreen(Screen):
    def do_login(self):
        user_name = self.ids.name_input.text.strip()
        if user_name:
            self.manager.chat_client = ChatClient(user_id=user_name)
            store.put('user', name=user_name)
            self.manager.current = "menu"
        else:
            self.ids.name_input.text = ""
            self.ids.name_input.hint_text = "Digite um nome v\u00e1lido"

class MainMenuScreen(Screen):
    def go_to_individual(self):
        self.manager.current = "user_list"
    def go_to_create_group(self):
        self.manager.current = "create_group"

class UserListScreen(Screen):
    def on_enter(self):
        box = self.ids.users_box
        box.clear_widgets()
        users = self.manager.chat_client.request_users_online() if self.manager.chat_client else []
        current_user = self.manager.chat_client.user_id if self.manager.chat_client else ""
        for user in users:
            if user != current_user:
                btn = Button(text=user, size_hint_y=None, height=40)
                btn.bind(on_press=self.select_user)
                box.add_widget(btn)
    def select_user(self, instance):
        chat_screen = self.manager.get_screen("chat")
        chat_screen.recipient = instance.text
        chat_screen.is_group = False
        chat_screen.ids.current_chat_label.text = f"Conversa com {instance.text}"
        self.manager.current = "chat"

class CreateGroupScreen(Screen):
    selected_users = []
    def on_enter(self):
        self.selected_users = []
        box = self.ids.group_users_box
        box.clear_widgets()
        users = self.manager.chat_client.request_users_online() if self.manager.chat_client else []
        current_user = self.manager.chat_client.user_id if self.manager.chat_client else ""
        for user in users:
            if user != current_user:
                btn = Button(text=user, size_hint_y=None, height=40)
                btn.bind(on_press=self.toggle_user)
                box.add_widget(btn)
    def toggle_user(self, instance):
        user = instance.text
        if user in self.selected_users:
            self.selected_users.remove(user)
            instance.background_color = (1, 1, 1, 1)
        else:
            self.selected_users.append(user)
            instance.background_color = (0, 1, 0, 1)
    def create_group_action(self):
        if not self.selected_users:
            print("Nenhum usu\u00e1rio selecionado para o grupo")
            return
        # Gera um ID de grupo simples; por exemplo, juntando os nomes selecionados
        group_id = "grupo_" + "_".join(sorted(self.selected_users))
        current_user = self.manager.chat_client.user_id
        members = [current_user] + self.selected_users
        response = self.manager.chat_client.create_group(group_id, members)
        print("Grupo criado:", response)
        chat_screen = self.manager.get_screen("chat")
        chat_screen.recipient = group_id
        chat_screen.is_group = True
        chat_screen.ids.current_chat_label.text = f"Grupo: {group_id}"
        self.manager.current = "chat"

class ChatScreen(Screen):
    recipient = None
    is_group = False  # False para chat individual, True para grupo
    def __init__(self, **kwargs):
        super(ChatScreen, self).__init__(**kwargs)
        Clock.schedule_interval(self.fetch_messages, 1)
    def send_message(self):
        if not self.recipient:
            self.ids.chat_label.text += "\n[Erro] Nenhum destinat\u00e1rio selecionado!"
            return
        message = self.ids.message_input.text.strip()
        if message:
            if self.is_group:
                self.manager.chat_client.send_message(self.recipient, message, group=True)
                self.ids.chat_label.text += f"\nVocê [{self.recipient}]: {message}"
            else:
                self.manager.chat_client.send_message(self.recipient, message)
                self.ids.chat_label.text += f"\nVocê para {self.recipient}: {message}"
            self.ids.message_input.text = ""
    def fetch_messages(self, dt):
        if not self.manager.chat_client:
            return
        messages = self.manager.chat_client.fetch_messages()
        for msg in messages:
            if msg.get('group'):
                self.ids.chat_label.text += f"\n{msg['from']} [{msg['group']}]: {msg['message']}"
            else:
                self.ids.chat_label.text += f"\n{msg['from']}: {msg['message']}"

class ChatApp(App):
    def build(self):
        sm = Builder.load_string(kv)
        sm.chat_client = None
        if store.exists('user'):
            user_name = store.get('user')['name']
            sm.chat_client = ChatClient(user_id=user_name)
            sm.current = "menu"
        else:
            sm.current = "login"
        return sm

if __name__ == '__main__':
    ChatApp().run()

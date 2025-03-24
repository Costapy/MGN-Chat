import asyncio
import websockets

async def client():
    try:
        async with websockets.connect("ws://localhost:8765") as websocket:
            # Envia o username
            username = "user1"
            await websocket.send(username)
            print(f"Conectado como {username}")

            # Envia uma mensagem para user2
            recipient = "user2"
            message = "Olá, user2!"
            await websocket.send(f"{recipient}:{message}")
            print(f"Mensagem enviada para {recipient}: {message}")

            # Recebe mensagens
            while True:
                try:
                    message = await websocket.recv()
                    print(f"Mensagem recebida: {message}")
                except websockets.ConnectionClosed:
                    print("Conexão fechada pelo servidor.")
                    break  # Sai do loop se a conexão for fechada
    except Exception as e:
        print(f"Erro ao conectar ao servidor: {e}")

# Executa o cliente
asyncio.run(client())
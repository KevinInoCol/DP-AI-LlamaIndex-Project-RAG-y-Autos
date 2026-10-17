import telebot
import os
from dotenv import load_dotenv
from telegram_interface import initialize, chat

# Cargar variables de entorno desde .env
load_dotenv()

# Obtener las variables de entorno
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BOT_NAME = os.getenv("BOT_NAME")

# Validar que las variables estén definidas
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY no está definida en el archivo .env")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN no está definida en el archivo .env")

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
Telegram_bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

print(f"🤖 Inicializando {BOT_NAME}...")
print(f"📝 Token del bot configurado: {TELEGRAM_BOT_TOKEN[:10]}...")

# Verificar que el bot pueda conectarse
try:
    bot_info = Telegram_bot.get_me()
    print(f"✅ Bot conectado: @{bot_info.username} ({bot_info.first_name})")
except Exception as e:
    print(f"❌ Error al conectar con Telegram: {e}")
    raise

# ═══════════════════════════════════════════════════
# Inicializar el Agente IA con memoria persistente
# ═══════════════════════════════════════════════════
initialize(bot_name=BOT_NAME)
print("✅ Bot listo y escuchando mensajes...")


@Telegram_bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = str(message.chat.id)
    user_name = message.from_user.username or message.from_user.first_name or "Usuario"

    print(f"📨 Comando /start recibido de {user_name} (Chat ID: {chat_id})")

    try:
        welcome_message = (
            f"¡Mucho gusto! Soy tu asistente {BOT_NAME} y estoy para servirte "
            "en cualquier consulta relacionada a nuestra tienda de vehículos."
        )
        Telegram_bot.send_message(message.chat.id, welcome_message)
        print("✅ Mensaje de bienvenida enviado")
    except Exception as e:
        print(f"❌ Error al enviar mensaje: {e}")


@Telegram_bot.message_handler(func=lambda message: message.text and message.text.lower() in ['adiós', 'chau', 'hasta luego', 'bye', 'después vuelvo'])
def goodbye(message):
    chat_id = str(message.chat.id)
    user_name = message.from_user.username or message.from_user.first_name or "Usuario"

    print(f"👋 Mensaje de despedida recibido de {user_name}")

    try:
        Telegram_bot.send_message(message.chat.id, "¡Hasta pronto!")
        print("✅ Mensaje de despedida enviado")
    except Exception as e:
        print(f"❌ Error al enviar mensaje de despedida: {e}")


@Telegram_bot.message_handler(content_types=['text'])
def send_text(message):
    if not message.text:
        return

    chat_id = str(message.chat.id)
    user_name = message.from_user.username or message.from_user.first_name or "Usuario"
    user_message = message.text

    print(f"📨 Mensaje recibido de {user_name} (Chat ID: {chat_id}): {user_message[:50]}...")

    try:
        # Enviar "escribiendo..."
        Telegram_bot.send_chat_action(message.chat.id, 'typing')

        # ═══════════════════════════════════════════════
        # Consultar al Agente IA
        # La memoria se carga/guarda automáticamente
        # ═══════════════════════════════════════════════
        print("🤖 Consultando al agente...")
        response_text = chat(user_message, chat_id)
        print(f"📝 Respuesta del agente: {response_text[:100]}...")

        Telegram_bot.send_message(message.chat.id, response_text)
        print(f"✅ Respuesta enviada a {user_name}")

    except Exception as e:
        import traceback
        error_msg = "Lo siento, ocurrió un error al procesar tu mensaje. Por favor, inténtalo de nuevo."
        print(f"❌ Error al procesar mensaje: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")
        try:
            Telegram_bot.send_message(message.chat.id, error_msg)
        except:
            pass


print("🚀 Iniciando bot de Telegram...")
print("=" * 60)
print("📡 Esperando mensajes...")
print("=" * 60)
print(f"✅ Handlers registrados:")
print(f"   - /start")
print(f"   - Mensajes de despedida")
print(f"   - Mensajes de texto (via Agente FunctionAgent)")
print("=" * 60)

# Iniciar polling
print("🔄 Iniciando polling...")
Telegram_bot.polling()

import os
import logging
import asyncio
import ipaddress
import socket
from datetime import datetime

from utils import ServerManager, get_geo_ip
from marzban_node_api import NodeSetup

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import BaseFilter, Command
from aiogram.enums import ParseMode


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

ADMIN_IDS = [
    int(os.getenv("TG_CHAT_ID", "0")),
]

marzban_api = NodeSetup(
    os.getenv("MARZBAN_USERNAME"),
    os.getenv("MARZBAN_PASSWORD"),
    os.getenv("MARZBAN_URL"),
)


def log_admin_action(user_id: int, action: str, details: str = ""):
    """Log admin actions"""
    logger.info(f"ADMIN_ACTION: User {user_id} - {action} - {details}")


def validate_ip_address(ip: str) -> bool:
    """Validate IP address"""
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def check_port_availability(ip: str, port: int) -> bool:
    """Check port availability"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except Exception:
        return False


class IsAdmin(BaseFilter):
    async def __call__(self, message: types.Message) -> bool:
        return message.from_user.id in ADMIN_IDS


bot = Bot(token=os.getenv("TG_BOT_TOKEN"))
dp = Dispatcher(storage=MemoryStorage())
dp.message.filter(IsAdmin())


class NodeConfig(StatesGroup):
    waiting_for_ip = State()
    waiting_for_password = State()
    waiting_for_ports = State()


class NodeManagement(StatesGroup):
    waiting_for_delete_confirmation = State()


def get_main_keyboard():
    """Main keyboard with four main functions"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔧 Configure Node")],
            [KeyboardButton(text="📋 Nodes")],
            [KeyboardButton(text="📊 Statistics")],
            [KeyboardButton(text="❓ Help")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Select action",
    )
    return keyboard


def get_cancel_keyboard():
    """Cancel keyboard"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Cancel node creation")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    return keyboard


def get_ports_keyboard():
    """Keyboard with suggested ports"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="8443:8880 (Default)", callback_data="ports_8443_8880"
                )
            ],
            [InlineKeyboardButton(text="Enter manually", callback_data="ports_manual")],
        ]
    )
    return keyboard


def get_delete_confirmation_keyboard(node_id: str, node_name: str):
    """Delete confirmation keyboard"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Yes, delete", callback_data=f"delete_yes_{node_id}"
                ),
                InlineKeyboardButton(text="❌ No, cancel", callback_data="delete_no"),
            ]
        ]
    )
    return keyboard


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Greeting and brief guide"""
    user_id = message.from_user.id

    if user_id not in ADMIN_IDS:
        log_admin_action(
            user_id, "UNAUTHORIZED_ACCESS", f"User {user_id} tried to access bot"
        )
        await message.answer("🚫 You don't have access to this bot.")
        return

    log_admin_action(user_id, "BOT_STARTED")

    welcome_text = """
🤖 <b>Welcome to Marzban Node Manager!</b>

This bot will help you manage Marzban nodes:

🔧 <b>Configure Node</b> - Configure a new node on the server
📋 <b>Nodes</b> - View and manage existing nodes  
❓ <b>Help</b> - Detailed guide on how to use
📊 <b>Statistics</b> - Node usage statistics

Select the desired action from the keyboard below.
    """

    await message.answer(
        welcome_text, reply_markup=get_main_keyboard(), parse_mode=ParseMode.HTML
    )


@dp.message(F.text == "🔧 Configure Node")
async def configure_node_start(message: types.Message, state: FSMContext):
    """Start node configuration"""
    await message.answer(
        "Enter the server IP address:\n\n💡 Format: 192.168.1.100",
        reply_markup=get_cancel_keyboard(),
    )
    await state.set_state(NodeConfig.waiting_for_ip)


@dp.message(F.text == "❌ Cancel node creation")
async def cancel_node_creation(message: types.Message, state: FSMContext):
    """Cancel node creation"""
    await state.clear()
    await message.answer("❌ Node creation canceled.", reply_markup=get_main_keyboard())


@dp.message(NodeConfig.waiting_for_ip)
async def process_ip(message: types.Message, state: FSMContext):
    """Processing IP address"""
    user_id = message.from_user.id
    ip = message.text.strip()

    try:
        if not validate_ip_address(ip):
            await message.answer(
                "❌ Invalid IP address format. Please try again.\n\n💡 Example: 192.168.1.100",
                reply_markup=get_cancel_keyboard(),
            )
            return

        if ip in ["127.0.0.1", "localhost", "::1"]:
            await message.answer(
                "❌ Cannot use localhost. Enter the external IP address of the server.",
                reply_markup=get_cancel_keyboard(),
            )
            return

        await message.answer("🔍 Checking server availability...")
        if not check_port_availability(ip, 22):
            await message.answer(
                "⚠️ Attention: SSH port (22) is not available. Ensure the server is running and accessible.",
                reply_markup=get_cancel_keyboard(),
            )

        await state.update_data(ip=ip)
        log_admin_action(user_id, "IP_ENTERED", f"IP: {ip}")

        await message.answer(
            "Enter the server password:\n\n🔒 The password will only be used for configuration and will not be saved",
            reply_markup=get_cancel_keyboard(),
        )
        await state.set_state(NodeConfig.waiting_for_password)

    except Exception as e:
        logger.error(f"Error processing IP {ip}: {str(e)}")
        await message.answer(
            "❌ An error occurred while processing the IP address. Please try again.",
            reply_markup=get_cancel_keyboard(),
        )


@dp.message(NodeConfig.waiting_for_password)
async def process_password(message: types.Message, state: FSMContext):
    """Processing password"""
    user_id = message.from_user.id
    password = message.text.strip()

    if not password:
        await message.answer(
            "❌ Password cannot be empty. Please try again.",
            reply_markup=get_cancel_keyboard(),
        )
        return

    log_admin_action(
        user_id, "PASSWORD_ENTERED", "Password length: " + str(len(password))
    )

    await state.update_data(password=password)

    await message.answer(
        "Select the ports for the node or enter them manually:",
        reply_markup=get_ports_keyboard(),
    )


@dp.callback_query(F.data.startswith("ports_"))
async def process_ports_selection(callback: types.CallbackQuery, state: FSMContext):
    """Processing port selection"""
    await callback.answer()

    if callback.data == "ports_manual":
        await callback.message.answer(
            "Enter the ports in the format service_port:api_port\n\n💡 Example: 8443:8880",
            reply_markup=get_cancel_keyboard(),
        )
        await state.set_state(NodeConfig.waiting_for_ports)
    else:
        ports = callback.data.replace("ports_", "").split("_")
        service_port, api_port = int(ports[0]), int(ports[1])

        await process_node_setup(callback.message, state, service_port, api_port)


@dp.message(NodeConfig.waiting_for_ports)
async def process_ports_manual(message: types.Message, state: FSMContext):
    """Processing manual port input"""
    try:
        parts = message.text.split(":")
        if len(parts) != 2:
            raise ValueError("Invalid format. Use: service_port:api_port")
        service_port, api_port = int(parts[0].strip()), int(parts[1].strip())
        await process_node_setup(message, state, service_port, api_port)
    except ValueError as e:
        await message.answer(
            f"❌ Invalid port format: {str(e)}. Please try again.\n\n💡 Example: 8443:8880",
            reply_markup=get_cancel_keyboard(),
        )


async def process_node_setup(
    message: types.Message, state: FSMContext, service_port: int, api_port: int
):
    """Main node setup logic"""
    user_id = message.from_user.id
    data = await state.get_data()

    log_admin_action(
        user_id,
        "NODE_SETUP_STARTED",
        f"IP: {data['ip']}, Ports: {service_port}:{api_port}",
    )

    progress_msg = await message.answer("🔄 Starting node setup...")

    try:
        await progress_msg.edit_text("📡 Connecting to the server...")
        server_manager = ServerManager(data["ip"], data["password"])

        await progress_msg.edit_text("⚙️ Configuring the server...")
        setup_result = server_manager.setup_marzban_node(service_port, api_port)

        if not setup_result["success"]:
            log_admin_action(
                user_id,
                "NODE_SETUP_FAILED",
                f"Server setup failed: {setup_result['error']}",
            )
            await progress_msg.edit_text(
                f"❌ Server setup failed: {setup_result['error']}"
            )
            await state.clear()
            await message.answer("Select action:", reply_markup=get_main_keyboard())
            return

        await progress_msg.edit_text("✅ Server configured successfully!")

        await progress_msg.edit_text("🔗 Adding node to Marzban...")

        node_name = f"{get_geo_ip(data['ip'])}"
        marzban_api.create_node(
            name=node_name,
            address=data["ip"],
            port=service_port,
            api_port=api_port,
            new_host=True,
        )

        log_admin_action(
            user_id, "NODE_SETUP_COMPLETED", f"Node: {node_name}, IP: {data['ip']}"
        )

        await progress_msg.edit_text(
            f"✅ Node added successfully!\n\n📋 Node information:\n"
            f"• Name: {node_name}\n"
            f"• Address: {data['ip']}\n"
            f"• Port: {service_port}\n"
            f"• API port: {api_port}\n"
            f"• Creation time: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )

    except Exception as e:
        log_admin_action(user_id, "NODE_SETUP_ERROR", f"Error: {str(e)}")
        logger.error(f"Node setup error for user {user_id}: {str(e)}")
        await progress_msg.edit_text(f"❌ Error: {str(e)}")

    finally:
        await state.clear()
        await message.answer("Select action:", reply_markup=get_main_keyboard())


@dp.message(F.text == "📋 Nodes")
async def show_nodes(message: types.Message):
    """Show node list"""
    try:
        await message.answer("📋 Loading node list...")

        nodes = marzban_api.get_nodes()

        if not nodes:
            await message.answer("📭 Nodes not found.")
            return

        keyboard = InlineKeyboardMarkup(inline_keyboard=[])

        for node in nodes:
            node_info = (
                f"🗑️ {node.get('name', 'Unknown')} ({node.get('address', 'N/A')})"
            )
            keyboard.inline_keyboard.append(
                [
                    InlineKeyboardButton(
                        text=node_info, callback_data=f"node_{node['id']}"
                    )
                ]
            )

        await message.answer("Select a node to manage:", reply_markup=keyboard)

    except Exception as e:
        await message.answer(f"❌ Error loading nodes: {str(e)}")


@dp.callback_query(F.data.startswith("node_"))
async def node_management(callback: types.CallbackQuery, state: FSMContext):
    """Node management"""
    await callback.answer()

    node_id = callback.data.replace("node_", "")

    try:
        nodes = marzban_api.get_nodes()
        node = next((n for n in nodes if str(n["id"]) == node_id), None)

        if not node:
            await callback.message.answer("❌ Node not found.")
            return

        node_info = f"📋 <b>Node information:</b>\n\n"
        node_info += f"• ID: {node['id']}\n"
        node_info += f"• Name: {node.get('name', 'N/A')}\n"
        node_info += f"• Address: {node.get('address', 'N/A')}\n"
        node_info += f"• Port: {node.get('port', 'N/A')}\n"
        node_info += f"• API port: {node.get('api_port', 'N/A')}\n"
        node_info += f"• Status: {'🟢 Active' if node.get('status') else '🔴 Inactive'}"

        await callback.message.answer(
            node_info,
            reply_markup=get_delete_confirmation_keyboard(
                node_id, node.get("name", "Unknown")
            ),
            parse_mode=ParseMode.HTML,
        )

    except Exception as e:
        await callback.message.answer(f"❌ Error: {str(e)}")


@dp.callback_query(F.data.startswith("delete_"))
async def delete_node_confirmation(callback: types.CallbackQuery, state: FSMContext):
    """Node deletion confirmation"""
    user_id = callback.from_user.id
    await callback.answer()

    if callback.data == "delete_no":
        log_admin_action(user_id, "NODE_DELETE_CANCELLED")
        await callback.message.answer("❌ Deletion canceled.")
        return

    if callback.data.startswith("delete_yes_"):
        node_id = callback.data.replace("delete_yes_", "")

        log_admin_action(user_id, "NODE_DELETE_STARTED", f"Node ID: {node_id}")

        try:
            nodes = marzban_api.get_nodes()
            node = next((n for n in nodes if str(n["id"]) == node_id), None)

            if not node:
                await callback.message.answer("❌ Node not found.")
                return

            node_name = node.get("name", "Unknown")
            node_address = node.get("address", "N/A")

            progress_msg = await callback.message.answer("🗑️ Deleting node...")

            marzban_api.delete_node(node_id)

            log_admin_action(
                user_id,
                "NODE_DELETE_COMPLETED",
                f"Node: {node_name}, IP: {node_address}",
            )

            await progress_msg.edit_text(
                f"✅ Node deleted successfully!\n\n📋 Deleted node:\n"
                f"• Name: {node_name}\n"
                f"• Address: {node_address}\n"
                f"• Deletion time: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            )

        except Exception as e:
            log_admin_action(user_id, "NODE_DELETE_ERROR", f"Error: {str(e)}")
            logger.error(f"Node delete error for user {user_id}: {str(e)}")
            await callback.message.answer(f"❌ Error deleting node: {str(e)}")


@dp.message(F.text == "❓ Help")
async def show_help(message: types.Message):
    """Show help"""
    user_id = message.from_user.id
    log_admin_action(user_id, "HELP_REQUESTED")

    help_text = """
📚 <b>Marzban Node Manager Guide</b>

🔧 <b>Configure Node</b> - Node configuration:
1. Enter the server IP address (automatic validation)
2. Enter the server password  
3. Select ports (8443:8880 by default or enter manually)
4. The bot will automatically configure the server and add the node to Marzban
5. The progress indicator will show the setup steps

📋 <b>Nodes</b> - Node management:
• View the list of all nodes
• Detailed information about each node
• Ability to delete nodes with confirmation
• Logging all operations

📊 <b>Statistics</b> - Node statistics:
• Total number of nodes
• Number of active/inactive nodes
• Distribution by countries
• Last update time

⚠️ <b>Important notes:</b>
• Ensure the server is accessible via SSH (port 22)
• The certificate is taken from the MARZBAN_NODE_CERT environment variable
• For the bot to work, you need administrator rights on the server
• You can cancel the node creation at any time
• All actions are logged for security

🛠️ <b>Technical support:</b>
Check:
• Server availability (port 22 check)
• Password correctness
• Certificate presence in the .env file
• Logs in the bot.log file

🔒 <b>Security:</b>
• All admin actions are logged
• Passwords are not saved in logs
• IP address validation
• Server availability check
    """

    await message.answer(help_text, parse_mode=ParseMode.HTML)


@dp.message(F.text == "📊 Statistics")
async def show_statistics(message: types.Message):
    """Show nodes statistics"""
    user_id = message.from_user.id
    log_admin_action(user_id, "STATISTICS_REQUESTED")

    try:
        await message.answer("📊 Loading statistics...")

        nodes = marzban_api.get_nodes()

        if not nodes:
            await message.answer("📭 Nodes not found.")
            return

        total_nodes = len(nodes)
        active_nodes = sum(1 for node in nodes if node.get("status"))
        inactive_nodes = total_nodes - active_nodes

        countries = {}
        for node in nodes:
            geo_info = get_geo_ip(node.get("address", ""))
            country = (
                geo_info.split("(")[-1].rstrip(")") if "(" in geo_info else "Unknown"
            )
            countries[country] = countries.get(country, 0) + 1

        stats_text = f"""
📊 <b>Marzban nodes statistics</b>

📈 <b>Total statistics:</b>
• Total nodes: {total_nodes}
• Active: {active_nodes} 🟢
• Inactive: {inactive_nodes} 🔴

🌍 <b>By countries:</b>
"""

        for country, count in sorted(
            countries.items(), key=lambda x: x[1], reverse=True
        ):
            stats_text += f"• {country}: {count} nodes\n"

        stats_text += f"\n📅 Updated: {datetime.now().strftime('%d.%m.%Y %H:%M')}"

        await message.answer(stats_text, parse_mode=ParseMode.HTML)

    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        await message.answer(f"❌ Error loading statistics: {str(e)}")


async def main():
    """Start bot"""
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

# Marzban Node Manager Bot

🤖 Telegram bot for managing Marzban nodes with advanced monitoring and security capabilities.

## ✨ Main Features

### 🔧 Node Management
- **Automatic setup** of nodes on servers via SSH
- **IP address validation** with availability checking
- **Progress indicators** for long operations
- **Management of existing nodes** (view, delete)

### 📊 Statistics
- **Node statistics** by countries and statuses
- **Real-time health monitoring** of nodes

### 🔒 Security
- **Logging of all admin actions**
- **Rate limiting** to prevent spam
- **Input data validation**
- **Secure password handling**

## 🚀 Installation and Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Environment Variables Setup
Create a `.env` file in the project root:

```env
# Telegram Bot Configuration
TG_BOT_TOKEN=your_telegram_bot_token_here
TG_CHAT_ID=your_telegram_chat_id_here

# Marzban Configuration
MARZBAN_USERNAME=your_marzban_username
MARZBAN_PASSWORD=your_marzban_password
MARZBAN_URL=http://your_marzban_instance.com

# Marzban Node Certificate (base64 encoded)
MARZBAN_NODE_CERT=your_base64_encoded_certificate_here
```

### 3. Start the Bot
```bash
python bot.py
```

## 📋 Usage

### Bot Commands:
- `/start` - Welcome and main menu
- `🔧 Configure Node` - Configure a new node
- `📋 Nodes` - Manage existing nodes
- `📊 Statistics` - Statistics and monitoring
- `❓ Help` - Detailed help

### Node Setup Process:
1. **Enter IP address** - automatic validation and availability check
2. **Enter password** - secure handling without logging
3. **Select ports** - predefined or manual input
4. **Automatic setup** - with progress indicators
5. **Add to Marzban** - automatic node registration

## 🔧 Technical Improvements

### Validation and Checks:
- ✅ IP address validation using `ipaddress`
- ✅ SSH port (22) availability check
- ✅ Protection against localhost usage
- ✅ Port format validation

### Logging:
- 📝 All admin actions are logged to `bot.log`
- 🔒 Passwords are not saved in logs
- ⏰ Timestamps for all operations
- 🎯 Detailed error information

### Statistics:
- 🌐 Node availability checking
- 📊 Statistics by countries and statuses

### Security:
- 🔐 Access rights verification
- 🚫 Protection against unauthorized access
- 📋 Logging of unauthorized access attempts

## 📁 Project Structure

```
marzban-node/
├── bot.py              # Main bot file
├── marzban_node_api.py # API for Marzban integration
├── utils.py            # Server utilities
├── requirements.txt    # Python dependencies
├── .env               # Environment variables
├── bot.log            # Bot logs
└── README.md          # Documentation
```

## 🛠️ Requirements

- Python 3.8+
- SSH access to servers
- Configured Marzban instance
- Telegram Bot Token

## 🔍 Logging

All actions are logged to `bot.log` in the format:
```
2024-01-01 12:00:00 - bot - INFO - ADMIN_ACTION: User 123456 - NODE_SETUP_STARTED - IP: 192.168.1.100, Ports: 8443:8880
```

## 🚨 Error Handling

The bot includes advanced error handling:
- Network errors when connecting to servers
- Marzban authentication errors
- Input data validation errors
- Timeouts for long operations

## 📈 Statistics

The bot provides detailed statistics:
- Total number of nodes
- Number of active/inactive nodes
- Distribution by geographic locations

## 🔄 Updates

### Version 2.0 - Current
- ✅ Enhanced IP address validation
- ✅ Action logging system
- ✅ Node health monitoring
- ✅ Statistics
- ✅ Progress indicators
- ✅ Enhanced error handling

## 🤝 Support

If you encounter problems:
1. Check logs in `bot.log` file
2. Ensure correct settings in `.env`
3. Check server and Marzban API availability
4. Ensure all dependencies are installed

## 📄 License

MIT License 
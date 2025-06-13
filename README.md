# No Ping

A Python-based network optimization tool for reducing game latency, similar to ExitLag.

## Features

- Game traffic detection and optimization
- Smart routing through WireGuard VPN
- Packet interception using WinDivert
- User-friendly interface for game selection

## Requirements

- Python 3.11+
- WinDivert 2.2.2+
- WireGuard
- Windows 10/11

## Installation

1. Clone the repository:
```bash
git clone https://github.com/iruiz2002/No-Ping.git
cd No-Ping
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Make sure WinDivert and WireGuard are properly installed on your system.

## Usage

1. Run the main script:
```bash
python src/main.py
```

2. Select your game from the list
3. The program will automatically optimize your connection

## Project Structure

```
No-Ping/
├── src/                    # Source code
│   ├── main.py            # Main application entry
│   ├── network/           # Network handling
│   ├── vpn/              # VPN configuration
│   └── ui/               # User interface
├── config/                # Configuration files
├── tests/                 # Test files
└── requirements.txt       # Python dependencies
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT](https://choosealicense.com/licenses/mit/) 
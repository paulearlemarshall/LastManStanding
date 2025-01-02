# Last Man Standing

## Overview

The **Last Man Standing** project is a web application designed to fetch English Premier League (EPL) odds and strategize team selections for users. The application provides a user-friendly interface to manage player picks and analyze odds data, helping users make informed decisions.

## Features

- Fetches live EPL odds data from an external source.
- Displays match information in a structured and sortable table format.
- Allows users to select teams and manage their previous picks.
- Provides a strategizing feature to find optimal team selections based on user input.
- Debug logging for tracking application behavior and errors.

## Technologies Used

- **Backend**: Flask (Python)
- **Frontend**: HTML, CSS, JavaScript
- **Web Scraping**: BeautifulSoup, Requests
- **Data Handling**: Pandas
- **Caching**: Flask-Caching
- **Logging**: Python logging module

## Installation

### Prerequisites

- Python 3.x
- Flask
- Flask-Caching
- BeautifulSoup4
- Requests
- Pandas

### Steps to Install

1. Clone the repository:
   ```bash
   git clone https://github.com/paulearlemarshall/LastManStanding.git
   cd LastManStanding
   ```

2. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:
   ```bash
   python app.py
   ```

5. Open your web browser and navigate to `http://127.0.0.1:5000/`.

## Usage

- Click the "Fetch Odds" button to retrieve the latest odds data.
- Use the dropdowns to select teams for each player.
- Click "Add Pick" to add a team to the player's previous picks.
- Use the "Strategise" button to find the best paths based on the selected teams and previous picks.

## Contributing

Contributions are welcome! If you have suggestions for improvements or new features, please open an issue or submit a pull request.

1. Fork the repository.
2. Create a new branch (`git checkout -b feature-branch`).
3. Make your changes and commit them (`git commit -m 'Add new feature'`).
4. Push to the branch (`git push origin feature-branch`).
5. Open a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Thanks to the contributors and the open-source community for their support.
- Special thanks to the developers of Flask, BeautifulSoup, and other libraries used in this project.

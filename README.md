# Crypto Coin Scanner

The Crypto Coin Scanner is a Streamlit web application that displays the top 10 cryptocurrencies with the highest positive percentage change in the last 24 hours. It fetches market data from the CoinGecko API, checks for tradability on Binance, and retrieves related news/web results using the Brave Search API.

## Features

*   Displays Top 10 cryptocurrencies by 24-hour price increase.
*   Integrates CoinGecko API for market data.
*   Integrates Binance API to check for USDT trading pairs and fetch price/volume.
*   Integrates Brave Search API for fetching recent news/web results for each coin.
*   Modern, clean Altair chart for visualizing percentage gains.
*   Allows users to input their own API keys.
*   Option to export displayed data to CSV.

## Prerequisites

*   Python 3.8+
*   Pip (Python package installer)

## Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Vitor-VarelAI/Crypto-Coin-Scanner.git
    cd Coin-Scanner
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up API Keys:**
    Create a file named `.env` in the project root directory. Copy the contents of `.env.example` (which we will create next) into `.env` and fill in your API keys:
    ```env
    COINGECKO_API_KEY="YOUR_COINGECKO_API_KEY"  # Optional, but recommended for higher rate limits
    BRAVE_SEARCH_API_KEY="YOUR_BRAVE_SEARCH_API_KEY" # Required for news fetching
    ```
    Alternatively, you can enter the API keys directly in the application's sidebar when you run it.

## Running the Application

Once the setup is complete, run the Streamlit application:

```bash
streamlit run app.py
```

The application will open in your web browser.

## Project Structure

*   `app.py`: Main Streamlit application code.
*   `requirements.txt`: Python dependencies.
*   `.env`: Stores API keys (ignored by Git).
*   `.env.example`: Template for the `.env` file.
*   `.gitignore`: Specifies intentionally untracked files that Git should ignore.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the [MIT License](LICENSE) (assuming you choose MIT, we can create this file next).

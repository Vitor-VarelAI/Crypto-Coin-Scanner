import streamlit as st
import pandas as pd
import requests
import os
from dotenv import load_dotenv
from datetime import datetime
import time # for rate limiting example
import csv
from io import StringIO
import math
import altair as alt

load_dotenv() # Carrega variáveis do arquivo .env

# --- Page Configuration ---
st.set_page_config(
    page_title="Crypto Coin Scanner",
    page_icon="📊",
    layout="wide"
)

# --- Main Application ---
st.title("📊 Crypto Coin Scanner")
st.markdown("Mostra as moedas com maior subida nas últimas 24h (Top 10).")
st.warning("⚠️ Os dados são aproximados. Variações podem ocorrer entre fontes. Confirmar sempre antes de tomar decisões.")

# --- API Key Input (within Expander) ---
st.sidebar.header("Configurações")
api_key_env = os.getenv("COINGECKO_API_KEY")
api_key_value = api_key_env if api_key_env else ""

with st.sidebar.expander("🔑 Configurar API Key (Opcional)"):
    api_key_input_value = st.text_input(
        "Sobrescrever API Key (Demo)", 
        type="password", 
        value="", # Start empty to encourage using .env
        help="Deixe em branco para usar a chave do .env (se configurada)."
    )
    if api_key_env:
        st.caption(f"Chave do .env: ...{api_key_env[-4:] if len(api_key_env) > 4 else '****'}")
    else:
        st.caption("Nenhuma API Key configurada no .env")

# Determine API key to use
if api_key_input_value: # User provided input in the expander
    api_key = api_key_input_value
elif api_key_env: # .env key exists and expander input is empty
    api_key = api_key_env
else: # No key from expander or .env
    api_key = ""

# --- Brave Search API Key Input (within Expander) ---
brave_api_key_env = os.getenv("BRAVE_SEARCH_API_KEY")
brave_api_key_value = brave_api_key_env if brave_api_key_env else ""

with st.sidebar.expander("🔑 Configurar Brave Search API Key (Opcional)"):
    brave_api_key_input_value = st.text_input(
        "Sobrescrever Brave API Key", 
        type="password", 
        value="", # Start empty
        help="Deixe em branco para usar a chave do .env (se configurada)."
    )
    if brave_api_key_env:
        st.caption(f"Chave Brave do .env: ...{brave_api_key_env[-4:] if len(brave_api_key_env) > 4 else '****'}")
    else:
        st.caption("Nenhuma Brave API Key configurada no .env")

# Determine Brave API key to use
if brave_api_key_input_value:
    brave_api_key = brave_api_key_input_value
elif brave_api_key_env:
    brave_api_key = brave_api_key_env
else:
    brave_api_key = ""

# --- Helper Functions ---
def get_top_gainers(key):
    """Fetches the top gaining coins from CoinGecko API."""
    if not key:
        st.warning("Por favor, insira a API Key para buscar os dados.")
        return None

    all_coins_data = []
    base_url = "https://api.coingecko.com/api/v3/coins/markets"
    headers = {"x-cg-demo-api-key": key}
    
    for page_num in [1, 2]:
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 100,
            "page": page_num,
            "sparkline": "false",
            "price_change_percentage": "24h"
        }
        try:
            response = requests.get(base_url, headers=headers, params=params, timeout=10)
            response.raise_for_status()  # Raises an exception for 4XX/5XX errors
            page_data = response.json()
            if page_data:
                all_coins_data.extend(page_data)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                st.error("API Key inválida ou não autorizada. Verifique sua chave e tente novamente.")
                return None # Critical error, stop
            elif e.response.status_code == 429:
                st.error(f"Limite de requisições da API atingido (tentativa na página {page_num}).")
                if not all_coins_data: # If rate limited and no data yet from previous pages
                    return None
                break # Stop trying further pages, proceed with data collected so far
            else: # Other HTTP errors
                st.error(f"Erro HTTP {e.response.status_code} ao buscar dados da página {page_num}.")
                if not all_coins_data: return None
                break
        except requests.exceptions.RequestException as e: # Covers connection errors, timeouts, etc.
            st.error(f"Erro de conexão ao buscar dados da página {page_num}: {e}")
            if not all_coins_data:
                return None
            break # Stop trying further pages
        except Exception as e: # Catch other potential errors like JSONDecodeError
            st.error(f"Ocorreu um erro inesperado ao processar dados da página {page_num}: {e}")
            if not all_coins_data:
                return None
            break

    if not all_coins_data:
        st.warning("Nenhuma moeda foi encontrada após as tentativas de busca. Verifique a API Key e a conexão.")
        return None

    # Deduplicate coins using 'id' as a unique identifier, last seen instance prevails
    unique_coins_map = {coin['id']: coin for coin in all_coins_data}
    unique_coins_data = list(unique_coins_map.values())
    
    # Filter out coins with None for 'price_change_percentage_24h_in_currency'
    valid_coins = [
        coin for coin in unique_coins_data 
        if coin.get('price_change_percentage_24h_in_currency') is not None
    ]
    
    # Filter by minimum total volume
    filtered_by_volume = [
        coin for coin in valid_coins 
        if coin.get('total_volume') is not None and coin['total_volume'] > 1000000
    ]

    # Sort by 'price_change_percentage_24h_in_currency' in descending order
    sorted_coins = sorted(
        filtered_by_volume, 
        key=lambda x: x['price_change_percentage_24h_in_currency'], 
        reverse=True
    )
    
    if not sorted_coins:
        st.info("Nenhuma moeda atendeu aos critérios de volume e variação de preço após o processamento dos dados coletados.")
        return None
        
    return sorted_coins[:10]

# --- Helper Functions (Binance) ---
def get_binance_tradable_usdt_pairs():
    """Fetches all USDT trading pairs from Binance and caches them in session state."""
    if 'binance_usdt_pairs' not in st.session_state or st.session_state.binance_usdt_pairs is None:
        st.session_state.binance_usdt_pairs = set() # Default to empty set on error or if not fetched
        try:
            response = requests.get("https://api.binance.com/api/v3/exchangeInfo", timeout=10)
            response.raise_for_status()
            data = response.json()
            st.session_state.binance_usdt_pairs = {
                s['symbol'] for s in data['symbols'] 
                if s['quoteAsset'] == 'USDT' and s['status'] == 'TRADING'
            }
        except requests.exceptions.RequestException as e:
            st.sidebar.warning(f"⚠️ Erro ao buscar pares da Binance: {e}. Verificação da Binance pode falhar.")
        except Exception as e:
            st.sidebar.warning(f"⚠️ Erro inesperado ao processar pares da Binance: {e}.")
    return st.session_state.binance_usdt_pairs

def check_binance_data(coin_symbol, tradable_usdt_pairs):
    """
    Checks coin availability on Binance and fetches price and 24h volume.
    Uses a pre-fetched set of tradable USDT pairs.
    """
    binance_symbol_usdt = f"{coin_symbol.upper()}USDT"
    
    default_error_result = {
        "status_binance": "⚠️ Erro Verificação",
        "price_binance": "N/A",
        "volume_binance": "N/A"
    }

    if tradable_usdt_pairs is None or not isinstance(tradable_usdt_pairs, set):
        return {
            "status_binance": "❌ Verif. Indisponível",
            "price_binance": "N/A",
            "volume_binance": "N/A"
        }

    if not tradable_usdt_pairs: # If the set is empty due to a fetch error
        return {
            "status_binance": "⚠️ Binance Indisponível", # Cannot check due to earlier error
            "price_binance": "N/A",
            "volume_binance": "N/A"
        }

    if binance_symbol_usdt not in tradable_usdt_pairs:
        return {
            "status_binance": "❌ Não na Binance (USDT)",
            "price_binance": "N/A",
            "volume_binance": "N/A"
        }

    try:
        ticker_url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={binance_symbol_usdt}"
        response = requests.get(ticker_url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        price = float(data.get('lastPrice', 0))
        volume_usdt = float(data.get('quoteVolume', 0)) # Volume in USDT

        return {
            "status_binance": "✅ Na Binance",
            "price_binance": f"${price:,.8f}" if price < 0.01 else f"${price:,.2f}",
            "volume_binance": f"${volume_usdt:,.2f}"
        }
    except requests.exceptions.HTTPError as e:
        status_message = f"⚠️ Erro {e.response.status_code} Binance"
        if e.response.status_code == 400 and e.response.text and "Invalid symbol" in e.response.text:
             status_message = f"❌ {coin_symbol.upper()} Inválido (Ticker)"
        elif e.response.status_code == 404:
             status_message = f"❌ {coin_symbol.upper()} Não Listado (Ticker)"
        st.sidebar.warning(f"Erro HTTP {e.response.status_code} para {binance_symbol_usdt} na Binance.")
        return {**default_error_result, "status_binance": status_message}
    except requests.exceptions.RequestException:
        st.sidebar.warning(f"Erro de conexão para {binance_symbol_usdt} na Binance.")
        return {**default_error_result, "status_binance": "⚠️ Erro Conexão Binance"}
    except Exception as e:
        st.sidebar.warning(f"Erro ao processar dados de {binance_symbol_usdt} da Binance: {str(e)[:100]}")
        return {**default_error_result, "status_binance": f"⚠️ Erro Dados Binance"}

# --- Helper Function (Brave Search) ---
def get_brave_search_news(coin_name, b_api_key, count=3):
    """Fetches news for a coin using Brave Web Search API."""
    if not b_api_key:
        return {"error": "Brave Search API Key não fornecida."}
    if not coin_name:
        return {"error": "Nome da moeda não fornecido."}

    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": b_api_key
    }
    # Updated parameters for Web Search API
    params = {
        "q": f'{coin_name} coin news', # More specific query including 'coin'
        "count": count,
        "safesearch": "moderate",
        "freshness": "pd" # Past day results
        # No 'result_filter' means API returns all types (news, web, etc.)
        # "country": "us", # Optional: specify country
        # "search_lang": "en", # Optional: specify search language
    }
    try:
        # Updated endpoint for Web Search API
        response = requests.get("https://api.search.brave.com/res/v1/web/search", headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Attempt to parse 'news' results first, then 'web' results as a fallback
        processed_items = []
        
        # 1. Try 'news' results from the 'news' field
        news_specific_data = data.get('news', {}) 
        news_specific_results = news_specific_data.get('results', [])

        if news_specific_results:
            for item in news_specific_results:
                title = item.get('title', 'N/A')
                url = item.get('url', '#')
                snippet = item.get('description', item.get('snippet', 'N/A')) 
                source = item.get('source', item.get('meta_url', {}).get('hostname', 'N/A')) 
                processed_items.append({
                    "title": title,
                    "url": url,
                    "snippet": snippet,
                    "source": source
                })
        
        # 2. If no 'news' specific results were found, try 'web' results from the 'web' field
        if not processed_items:
            general_web_data = data.get('web', {})
            general_web_results = general_web_data.get('results', [])
            if general_web_results:
                # Optional: st.sidebar.info(f"Mostrando resultados web gerais para {coin_name}...")
                for item in general_web_results:
                    title = item.get('title', 'N/A')
                    url = item.get('url', '#')
                    snippet = item.get('description', item.get('snippet', 'N/A')) 
                    source = item.get('source', item.get('meta_url', {}).get('hostname', 'N/A'))
                    processed_items.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet,
                        "source": source
                    })

        # 3. Return collected items if any, otherwise a 'not found' message
        if processed_items:
            return {"news": processed_items} # Keep the key "news" for consistency in display logic
        else:
            return {"message": f"Nenhuma notícia ou resultado web relevante encontrado para {coin_name} com os filtros atuais."}
    except requests.exceptions.HTTPError as e:
        error_message = f"Erro HTTP {e.response.status_code} com Brave Web Search API para {coin_name}."
        if e.response.status_code == 401:
            error_message += " Verifique sua Brave API Key."
        elif e.response.status_code == 429:
            error_message += " Limite de requisições da Brave API atingido."
        elif e.response.status_code == 403:
             error_message += " Acesso não autorizado à Brave API. Verifique sua subscrição ou endpoint."
        st.sidebar.warning(error_message)
        return {"error": error_message}
    except requests.exceptions.RequestException as e:
        st.sidebar.warning(f"Erro de conexão com Brave Web Search API para {coin_name}: {e}")
        return {"error": f"Erro de conexão com Brave Web Search API para {coin_name}."}
    except Exception as e: # Catch other potential errors like JSONDecodeError
        st.sidebar.warning(f"Erro inesperado ao buscar notícias para {coin_name} no Brave Web Search: {e}")
        return {"error": f"Erro inesperado ao buscar notícias para {coin_name}."}


# --- Data Fetching and State Update ---
if st.sidebar.button("🚀 Buscar Dados"):
    # Clear previous data from session state to ensure freshness
    st.session_state.pop('top_coins_data', None)
    st.session_state.pop('coins_df', None)
    st.session_state.pop('news_cache', None)  # Clear news cache on new data fetch
    st.session_state.pop('data_fetched_time_utc', None)

    if api_key:
        with st.spinner("Buscando dados do CoinGecko..."):
            top_coins_result = get_top_gainers(api_key)

        if top_coins_result:
            st.session_state.top_coins_data = top_coins_result
            st.session_state.data_fetched_time_utc = datetime.utcnow()

            coins_data_processed = []
            with st.spinner("Buscando informações de pares da Binance..."):
                tradable_usdt_pairs = get_binance_tradable_usdt_pairs()

            with st.spinner("Verificando moedas na Binance e processando dados..."):
                for coin in st.session_state.top_coins_data:
                    coin_symbol_upper = coin.get('symbol', 'N/A').upper()
                    binance_data = check_binance_data(coin_symbol_upper, tradable_usdt_pairs)
                    coins_data_processed.append({
                        "Nome": coin.get('name', 'N/A'),
                        "Símbolo": coin_symbol_upper,
                        "Preço CoinGecko (USD)": (
                            f"${coin.get('current_price', 0):.8f}" 
                            if coin.get('current_price', 0) < 0.01 
                            else f"${coin.get('current_price', 0):,.4f}"
                        ),
                        "% Subida (24h)": f"{coin.get('price_change_percentage_24h_in_currency', 0):.2f}%",
                        "Status Binance": binance_data['status_binance'],
                        "Preço Binance (USD)": binance_data['price_binance'],
                        "Volume Binance (24h)": binance_data['volume_binance'],
                    })
            st.session_state.coins_df = pd.DataFrame(coins_data_processed)
            st.success("Dados do CoinGecko e Binance processados!")
        # Error messages from get_top_gainers are displayed within the function
    else:
        st.sidebar.warning("API Key é obrigatória!")

# --- Main Display Area (conditionally shown if data is in session state) ---
if 'coins_df' in st.session_state and st.session_state.coins_df is not None and not st.session_state.coins_df.empty:
    df_to_display = st.session_state.coins_df
    raw_top_coins_for_chart_news = st.session_state.top_coins_data

    st.subheader("🏆 Top 10 Moedas com Maior Subida (24h)")
    if 'data_fetched_time_utc' in st.session_state:
        st.caption(f"📅 Dados obtidos em: {st.session_state.data_fetched_time_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    st.dataframe(df_to_display.set_index('Nome'), use_container_width=True)

    # --- Bar Chart of Top Gainers ---
    st.subheader("📈 Gráfico de Variação Percentual (24h)")
    
    chart_values = []
    chart_symbols = []
    if raw_top_coins_for_chart_news: # Check if the list of coins is not None and not empty
        for coin in raw_top_coins_for_chart_news:
            percentage_change_val = coin.get('price_change_percentage_24h_in_currency')
            # Ensure it's a number and finite. get_top_gainers should already ensure it's not None.
            if isinstance(percentage_change_val, (int, float)) and math.isfinite(percentage_change_val):
                chart_values.append(percentage_change_val)
                chart_symbols.append(coin.get('symbol', 'N/A').upper())
            # else: # Optional: log coins skipped due to invalid data for debugging
            #     print(f"Skipping coin {coin.get('symbol')} for chart due to invalid percentage change: {percentage_change_val}")

    if chart_values: # If we have valid, finite values to plot
        chart_df_final = pd.DataFrame({
            'Símbolo': chart_symbols,
            '% Subida (24h)': chart_values
        }).set_index('Símbolo')

        # Ensure the DataFrame is not empty after potential filtering and has the required column
        if not chart_df_final.empty and '% Subida (24h)' in chart_df_final.columns:
            # Explicitly cast to float and ensure it's a numeric type for the chart
            chart_df_final['% Subida (24h)'] = pd.to_numeric(chart_df_final['% Subida (24h)'], errors='coerce')
            chart_df_final.dropna(subset=['% Subida (24h)'], inplace=True) # Remove rows where conversion failed

            if not chart_df_final.empty:
                # st.caption("Dados para o gráfico:") # Optional: keep if you want to see the df
                # st.dataframe(chart_df_final) 

                # Ensure the DataFrame is sorted for a visually appealing horizontal bar chart
                # Typically, for horizontal bars, you might want the highest value at the top.
                # Altair sorts by y-axis encoding by default if not specified otherwise.
                # Let's sort by '% Subida (24h)' descending to have the largest bar at the top.
                chart_df_final_sorted = chart_df_final.sort_values(by='% Subida (24h)', ascending=False)

                chart = alt.Chart(chart_df_final_sorted.reset_index()).mark_bar().encode(
                    x=alt.X('% Subida (24h):Q', title='% Subida (24h)', axis=alt.Axis(format='%', labelAngle=0)),
                    y=alt.Y('Símbolo:N', title='Símbolo', sort='-x'), # Sort by the x-value (descending)
                    tooltip=['Símbolo:N', alt.Tooltip('% Subida (24h):Q', format='.2f')] # Tooltip with 2 decimal places
                ).properties(
                    title='Top 10 Moedas por Variação % (24h)',
                    height=alt.Step(40) # Controls bar thickness and spacing; adjust as needed
                ).configure_axis(
                    grid=False # Cleaner look without grid lines
                ).configure_view(
                    strokeWidth=0 # Remove border around the chart
                )
                st.altair_chart(chart, use_container_width=True)
            else:
                st.info("Não há dados numéricos válidos para exibir no gráfico após a conversão.")
        else:
            st.info("Não há dados válidos de variação percentual para exibir no gráfico após a filtragem.")
    else:
        # This handles cases where raw_top_coins_for_chart_news was empty, None, or all items had invalid/non-finite percentages
        st.info("Não há dados válidos para exibir no gráfico de variação percentual.")
    
    # Optional: Export to CSV
    csv_export_data = df_to_display.to_csv(index=False).encode('utf-8')
    current_time_utc_file = datetime.utcnow() # For filename uniqueness
    csv_filename = f"top_10_gainers_{current_time_utc_file.strftime('%Y%m%d_%H%M%S')}.csv"
    st.download_button(
        label="📥 Exportar para CSV",
        data=csv_export_data,
        file_name=csv_filename,
        mime='text/csv',
    )

    # --- Brave Search Context Section ---
    st.subheader("🔎 Contexto Web (Brave Search)")
    if brave_api_key: # brave_api_key is globally defined from sidebar input
        if st.button("📰 Buscar Notícias para Moedas Listadas (Brave)"):
            if 'news_cache' not in st.session_state:
                st.session_state.news_cache = {}

            with st.spinner("Buscando notícias no Brave Search..."):
                for index, row in df_to_display.iterrows(): # Iterate over the DataFrame from session state
                    coin_name_for_search = row['Nome'] 
                    if coin_name_for_search not in st.session_state.news_cache or not st.session_state.news_cache[coin_name_for_search]:
                        news_result = get_brave_search_news(coin_name_for_search, brave_api_key, count=3)
                        st.session_state.news_cache[coin_name_for_search] = news_result
                        time.sleep(1.1)  # Respect Brave API rate limit (1 req/sec)
                    else:
                        news_result = st.session_state.news_cache[coin_name_for_search]
                    
                    with st.expander(f"Notícias para {row['Símbolo']} ({coin_name_for_search})"):
                        if "news" in news_result and news_result["news"]:
                            for item in news_result["news"]:
                                st.markdown(f"**[{item['title']}]({item['url']})** - *{item['source']}*", unsafe_allow_html=True)
                                st.caption(item['snippet'])
                                st.markdown("---")
                        elif "message" in news_result:
                            st.info(news_result["message"])
                        elif "error" in news_result:
                            st.error(news_result["error"])
                        else:
                            st.info(f"Nenhuma informação de notícias para {coin_name_for_search}.")
    else:
        st.info("Configure a Brave Search API Key na barra lateral para buscar notícias.")

st.sidebar.markdown("---")
st.sidebar.markdown("Desenvolvido VVarelAI.")

![Logótipo](https://github.com/BacalhauNaBrisa/varredor_de_restaurantes/raw/main/assets/logo.png)

# Varredor de Restaurantes 🍽️

Esta aplicação permite explorar restaurantes numa cidade especificada, utilizando a API do Google Places. Através de uma grelha de coordenadas, é possível recolher uma grande quantidade de restaurantes de forma estruturada, visualizá-los num mapa e exportar os dados para CSV, Excel ou Google Sheets.

---

## 🧩 Funcionalidades Principais

- 🔍 Pesquisa em grelha com alta cobertura da área urbana  
- 📊 Avaliação ponderada por algoritmo bayesiano (Weighted Rating)  
- 🗺️ Visualização interativa no mapa  
- 📋 Tabela com filtros, ordenação e paginação (AgGrid)  
- 📥 Exportação para CSV e Excel  
- ☁️ Upload automático para Google Sheets (por cidade, numa aba específica)  
- ✅ Botão para limpar os resultados  

---

## 🚀 Como usar

1. Introduz o nome da cidade (ex: `Lagos, Portugal`)
2. Clica em "Pesquisar Restaurantes"
3. Aguarda enquanto os dados são recolhidos e processados
4. Visualiza os resultados na tabela e no mapa
5. Exporta os dados ou envia para o Google Sheets

---

## 🧪 Tecnologias usadas

- Python 3.13+
- Streamlit
- Google Places API v1
- Folium
- Pandas / Numpy
- gspread / Google Sheets API
- AgGrid via `st-aggrid`
- XlsxWriter

---

## 📁 Estrutura de pastas

📁 assets/
└── logo.png
└── favicon.png
📄 Restaurant Scraper (script principal)
📄 requirements.txt
📄 .streamlit/secrets.toml


---

## 🔐 Gestão de Segredos

Na [Streamlit Cloud](https://streamlit.io/cloud), insere as chaves API e credenciais no separador `Secrets` em TOML:

GOOGLE_API_KEY = "a-sua-chave-api"

[GOOGLE_SHEETS_CREDENTIALS]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "..."
client_email = "..."
client_id = "..."
...

⚠️ Limitações

  A Google Places API impõe limites de uso gratuitos diários e por minuto.

  O mapa pode não carregar em algumas redes corporativas restritivas.

  A criação do ficheiro Google Sheets exige partilha prévia com o serviço client_email da conta.

📡 Deploy

Esta aplicação pode ser publicada em:

  Streamlit Cloud

  Heroku, Railway, ou outras plataformas com suporte Python

📃 Licença

MIT © 2025 BacalhauNaBrisa

<p align="center">
  <img src="https://github.com/BacalhauNaBrisa/varredor_de_restaurantes/raw/main/assets/logo.png" alt="Varredor de Restaurantes" width="250"/>
</p>

# Varredor de Restaurantes

Este é um aplicativo Streamlit para buscar restaurantes em uma cidade usando a API Google Places v1, exibindo os resultados em tabela e mapa, e permitindo exportar dados para CSV, Excel e Google Sheets.

---

## Funcionalidades

- Proteção via passkey para acesso.
- Busca de restaurantes por cidade com grade de pontos para melhor cobertura.
- Cálculo de rating ponderado (considerando número de avaliações).
- Exibição dos resultados em tabela interativa (AgGrid) e mapa (Folium).
- Exportação dos resultados em CSV, Excel.
- Upload dos dados para Google Sheets via API.

---

## Requisitos

- Python 3.11 (recomendado para compatibilidade das dependências, especialmente `st-aggrid`)
- Bibliotecas listadas no `requirements.txt`

---

## Instalação

1. Clone o repositório:

```bash
git clone https://github.com/BacalhauNaBrisa/varredor_de_restaurantes.git
cd varredor_de_restaurantes

    Crie e ative um ambiente virtual (recomendado Python 3.11):

python3.11 -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

    Instale as dependências:

pip install -r requirements.txt

Configuração

Configure as seguintes variáveis secretas no Streamlit Cloud (Settings > Secrets):

ACCESS_PASSKEY = "sua_passkey_aqui"
GOOGLE_API_KEY = "sua_google_api_key_aqui"

[GOOGLE_SHEETS_CREDENTIALS]
type = "service_account"
project_id = "seu_project_id"
private_key_id = "seu_private_key_id"
private_key = """-----BEGIN PRIVATE KEY-----
...
-----END PRIVATE KEY-----"""
client_email = "seu_email_de_conta_de_servico"
client_id = "seu_client_id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "url_do_certificado_x509"
universe_domain = "googleapis.com"

Uso

    Execute o app:

streamlit run varredor_de_restaurantes.py

    Na interface web:

        Digite a passkey para liberar o acesso.

        Informe a cidade desejada.

        Clique em "Pesquisar Restaurantes".

        Aguarde a busca e carregamento dos dados.

        Visualize os restaurantes na tabela e no mapa.

        Exporte os dados para CSV, Excel ou envie para Google Sheets.

Notas

    A busca utiliza uma grade de pontos para melhor cobertura da área.

    A passkey é obrigatória para liberar o uso do app.

    O método st.experimental_rerun() é usado para reiniciar o app após o login com passkey.

    Para evitar problemas de compatibilidade, recomenda-se usar Python 3.11 pois st-aggrid ainda não suporta Python 3.13.

    Caso utilize Python 3.13, poderá haver erros na instalação do st-aggrid.

Dependências principais

    streamlit

    pillow

    requests

    folium

    gspread

    google-auth

    numpy

    pandas

    streamlit-folium

    st-aggrid

Licença

MIT License

# dashboardEnvira

Dashboard BI para monitoramento de alertas da Prefeitura Municipal de Envira.

## Stack Técnica

- **Dashboard**: Dash (Plotly)
- **Banco de dados**: PostgreSQL (Supabase)
- **Python**: 3.12

## Configuração

1. Criar ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

2. Instalar dependências:
```bash
pip install -r requirements.txt
```

3. Configurar variáveis de ambiente:
```bash
cp .env.example .env
# Editar .env com as credenciais do banco
```

4. Executar:
```bash
python app.py
```

Acesse: http://127.0.0.1:8050
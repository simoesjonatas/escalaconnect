# 🗓️ Escala Connect 🚀  
**Sistema de Gestão de Escalas e Eventos**  

Escala Connect é um sistema completo para gerenciamento de **eventos, escalas e planejamento de equipes**. Ele permite a criação de **eventos recorrentes**, associação de **funções a equipes**, organização de **escalas de trabalho** e **confirmação de disponibilidade dos usuários**.  

---

## ✨ Principais Funcionalidades  
✔ **Gerenciamento de Eventos** → Criação e edição de eventos com suporte a recorrência  
✔ **Planejamento de Equipes** → Definição de funções para cada evento  
✔ **Gestão de Escalas** → Associação de funções aos eventos de forma automatizada  
✔ **Confirmação de Escalas** → Usuários podem confirmar ou recusar escalas designadas  
✔ **Calendário Integrado** → Visualização interativa das escalas no calendário  
✔ **Controle de Acesso** → Apenas líderes e administradores podem editar escalas  
✔ **Sistema de Notificações** → Alertas para eventos e confirmações pendentes  

---

## 💻 Tecnologias Utilizadas  
- **Backend**: Django, Django REST Framework  
- **Frontend**: HTML, CSS, JavaScript (FullCalendar)  
- **Banco de Dados**: PostgreSQL  
- **Autenticação**: Django Authentication (com suporte a permissões)  
- **Implantação**: Docker & Kubernetes  

---

## 🛠 Como Rodar o Projeto  

### 1️⃣ Clone o repositório  
```bash
git clone https://github.com/seu-usuario/escala-connect.git
cd escala-connect
```
  
### 2️⃣ Crie e ative o ambiente virtual  
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate      # Windows
```

### 3️⃣ Instale as dependências  
```bash
pip install -r requirements.txt
```

### 4️⃣ Configure o banco de dados  
```bash
python manage.py migrate
python manage.py createsuperuser  # Opcional
```

### 5️⃣ Inicie o servidor local  
```bash
python manage.py runserver
```

### 6️⃣ Acesse no navegador  
```
http://127.0.0.1:8000/
```

---

## 🩺 Produção: monitoramento do Celery  
Push, lembretes e e-mails saem pelo Celery (serviços `celeryworker` e `celerybeat` do `docker-compose.yml`). Se eles param, o site continua no ar e ninguém percebe. Por isso:

- `docker compose ps` mostra `(healthy)`/`(unhealthy)` para o worker e o beat;
- o `web` manda e-mail aos `ADMINS` (padrão em `settings.py`, trocável pelo `.env`) quando a fila recusa tarefas ou o worker/beat param de bater;
- `GET /healthz/celery` responde 200 ou 503 com o diagnóstico, para cron ou monitor externo;
- Monitoramento > **Fila e push** (só superusuário) mostra a fila, as tarefas agendadas com a próxima execução e os últimos pushes.

Detalhes, cron sugerido e o que fazer ao receber o aviso: [docs/monitoramento-celery.md](docs/monitoramento-celery.md).

---

## 📝 Contribuição  
Contribuições são bem-vindas! Caso tenha sugestões ou encontre bugs, abra uma **Issue** ou envie um **Pull Request**.

---

## 📜 Licença  
Este projeto é distribuído sob a licença **MIT**.  

🔗 **GitHub Repository:** [https://github.com/simoesjonatas/escalaconnect.git](https://github.com/simoesjonatas/escalaconnect.git)  

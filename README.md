# Conecta-Zap 60+: Segurança e Autonomia Digital

O Conecta-Zap 60+ é um protótipo acadêmico de aplicação web para um projeto de extensão universitária. Ele organiza o envio de dez pílulas de conhecimento pelo WhatsApp para pessoas idosas, registra respostas e oferece um painel administrativo acessível.

O provedor padrão é totalmente local: nenhuma mensagem externa é enviada enquanto `MESSAGING_PROVIDER=mock`. A integração com o Twilio Sandbox é opcional.

## Objetivos

- Apoiar a autonomia digital de pessoas idosas com mensagens curtas em português brasileiro.
- Demonstrar consentimento, automação, envio de texto e imagem, respostas, feedback e acompanhamento.
- Oferecer um ambiente seguro para demonstrações acadêmicas sem depender de serviços externos.

## Funcionalidades

- Cadastro de participantes com telefone normalizado e mascarado no painel.
- Consentimento por meio do comando `INICIAR`.
- Comandos `AJUDA` e `SAIR`.
- Sequência de dez pílulas com imagem e atividade prática.
- Agendamento automático com APScheduler.
- Modo demonstração com intervalo em minutos, envio manual e execução acelerada.
- Modo real com envio diário em horário configurável.
- Histórico de envios, status, respostas e feedbacks.
- Reenvio administrativo explícito.
- Provedor mock local e integração opcional com Twilio.
- Webhooks para mensagens recebidas e atualizações de status.
- Autenticação HTTP Basic nas rotas administrativas.

## Arquitetura

```text
Browser / Twilio
       |
   FastAPI routers
       |
AutomationService ---- SchedulerService
       |                       |
MessagingProvider         APScheduler
  |          |
Mock       Twilio
       |
SQLAlchemy 2 + SQLite
```

- `app/routers`: páginas administrativas, cadastro e webhooks.
- `app/services`: regras da trilha, conteúdo, agendamento e provedores.
- `app/models.py`: modelos relacionais.
- `app/templates` e `app/static`: painel responsivo em Jinja2, CSS e JavaScript puro.
- `data/pills.json`: fonte inicial das dez pílulas.
- `scripts`: preparação do banco e geração das imagens provisórias.
- `tests`: testes automatizados do fluxo principal.

## Instalação no Windows

### 1. Pré-requisitos

Instale o Python 3.12 e confirme:

```powershell
python --version
```

### 2. Ambiente virtual

Na raiz do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Se a política do PowerShell bloquear a ativação, use apenas nesta sessão:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 3. Dependências

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configuração

```powershell
Copy-Item .env.example .env
```

Edite `.env` e troque obrigatoriamente `ADMIN_PASSWORD`. O arquivo `.env` é ignorado pelo Git e não deve ser versionado.

Configuração local recomendada:

```dotenv
MESSAGING_PROVIDER=mock
BASE_URL=http://localhost:8000
DEMO_INTERVAL_MINUTES=2
ADMIN_USERNAME=admin
ADMIN_PASSWORD=uma-senha-local-forte
```

`APP_TIMEZONE` define o fuso usado pelo agendador. O padrão é `America/Sao_Paulo`.

### 5. Banco e imagens

```powershell
python -m scripts.generate_placeholders
python -m scripts.seed_database
```

O seed é idempotente: registros existentes são atualizados pelo número de ordem. O banco SQLite padrão será criado como `conecta_zap.db`.

### 6. Execução local

```powershell
python run.py
```

Abra `http://localhost:8000/admin`. O navegador solicitará o usuário e a senha definidos no `.env`.

Alternativa sem recarga automática:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Uso do modo mock

Com `MESSAGING_PROVIDER=mock`, cada envio recebe um identificador `MOCK-*`, é registrado no banco e aparece como `delivered`. Nenhuma chamada externa é feita.

Para simular o consentimento pelo terminal:

```powershell
Invoke-WebRequest -Method Post `
  -Uri http://localhost:8000/webhooks/twilio/incoming `
  -ContentType "application/x-www-form-urlencoded" `
  -Body "From=whatsapp%3A%2B5511999999999&To=whatsapp%3A%2B14155238886&Body=INICIAR&MessageSid=SM-DEMO-1&NumMedia=0"
```

Depois, abra o participante no painel. É possível enviar a próxima pílula, executar todas as restantes, pausar, retomar, reiniciar ou reenviar uma pílula já entregue.

## Configuração do Twilio Sandbox

1. Crie ou acesse uma conta Twilio.
2. No Console, abra o Sandbox for WhatsApp e siga a instrução para conectar o telefone de teste.
3. Copie o Account SID, o Auth Token e o número remetente do Sandbox.
4. Configure localmente:

```dotenv
MESSAGING_PROVIDER=twilio
TWILIO_ACCOUNT_SID=seu-account-sid
TWILIO_AUTH_TOKEN=seu-auth-token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
BASE_URL=https://seu-endereco-publico
```

Nunca inclua essas credenciais em código, documentação, prints ou commits. O Auth Token não é escrito nos logs.

## Webhooks da Twilio

No campo **When a message comes in** do Sandbox, use:

```text
POST https://seu-endereco-publico/webhooks/twilio/incoming
```

Os envios realizados pela aplicação já informam:

```text
POST https://seu-endereco-publico/webhooks/twilio/status
```

O webhook de entrada aceita `application/x-www-form-urlencoded`, processa `From`, `To`, `Body`, `MessageSid`, `NumMedia` e `MediaUrl0`, e devolve TwiML válido.

Após confirmar que o endereço público e o proxy preservam corretamente a URL, habilite:

```dotenv
TWILIO_VALIDATE_SIGNATURE=true
```

Com validação ativa, chamadas sem uma assinatura Twilio válida recebem HTTP 403. Em produção, essa opção não deve permanecer desabilitada.

## Uso com túnel público

Durante uma demonstração, uma ferramenta como ngrok ou Cloudflare Tunnel pode expor a porta local:

```powershell
ngrok http 8000
```

Copie a URL HTTPS gerada para `BASE_URL`, reinicie a aplicação e configure os webhooks do Sandbox. URLs de mídia também usam `BASE_URL`; portanto, ela precisa ser pública para que a Twilio consiga buscar os PNGs.

O túnel é um serviço externo e não faz parte deste repositório. Confirme as políticas institucionais antes de expor dados.

## Modo demonstração

- Defina `mode=demo` no cadastro.
- O intervalo padrão é de dois minutos e pode ser alterado por `DEMO_INTERVAL_MINUTES`.
- O botão **Enviar próxima** envia apenas uma pílula.
- O botão **Executar demonstração** envia imediatamente todas as pílulas ainda não entregues.
- A demonstração acelerada somente funciona em participantes no modo demo.

O sistema nunca envia automaticamente a mesma pílula duas vezes. Uma repetição só ocorre pelo botão **Reenviar**.

## Modo real e janela de 24 horas

No modo real, o próximo envio é programado para `REAL_DELIVERY_HOUR` no fuso `APP_TIMEZONE`. Depois de cada pílula, o próximo horário é calculado para o dia seguinte.

O WhatsApp mantém uma janela de atendimento de 24 horas após a última mensagem do usuário. Mensagens iniciadas pela organização fora dessa janela podem exigir templates previamente aprovados pela Meta/Twilio. Este protótipo envia texto livre e não administra templates; antes de um uso real, adapte o conteúdo e o fluxo às regras atuais do WhatsApp Business e da Twilio.

## Testes

```powershell
pytest -q
```

Os testes usam um banco SQLite separado, provedor mock e agendador desabilitado. Eles cobrem:

- cadastro;
- `INICIAR` e `SAIR`;
- próxima pílula;
- bloqueio de duplicidade;
- conclusão da décima pílula;
- armazenamento de resposta;
- feedback estruturado;
- provedor mock;
- webhook;
- rota `/health`.

## Roteiro para demonstração

1. Inicie a aplicação em modo mock.
2. Cadastre uma pessoa no painel.
3. Simule `INICIAR` pelo webhook para confirmar o consentimento.
4. Mostre a mensagem de boas-vindas no histórico.
5. Envie a primeira pílula manualmente.
6. Simule uma resposta livre pelo webhook e mostre o vínculo à última pílula.
7. Execute a demonstração acelerada.
8. Mostre as dez entregas, a conclusão e a mensagem de feedback.
9. Envie `FEEDBACK 5 | SIM | Pix com segurança | SIM | Gostei`.
10. Volte à visão geral para mostrar os indicadores atualizados.

## Docker

```powershell
docker build -t conecta-zap .
docker run --rm -p 8000:8000 --env-file .env conecta-zap
```

Para persistir o SQLite em contêiner, ajuste `DATABASE_URL` para um caminho em volume montado. Não coloque o arquivo `.env` dentro da imagem publicada.

## Privacidade e consentimento

Este sistema é um protótipo acadêmico, não uma solução pronta para produção.

- Use dados fictícios em demonstrações sempre que possível.
- Colete consentimento livre e informado antes do primeiro conteúdo.
- Defina finalidade, base legal, prazo de retenção e responsáveis pelo tratamento.
- Aplique os princípios da LGPD, incluindo necessidade, transparência, segurança e livre acesso.
- Restrinja o acesso ao painel e troque a senha padrão.
- Defina um processo institucional para correção, exportação e exclusão de dados.
- Não envie informações sensíveis nas mensagens.
- Avalie criptografia, auditoria, backups e controle de acesso por usuário antes de usar dados reais.

O painel mascara telefones, mas o número completo permanece no banco porque é necessário para o envio. O protótipo não implementa rastreamento adicional.

## Limitações

- HTTP Basic é adequado apenas para demonstração controlada; produção exige autenticação com sessão, perfis e proteção contra tentativas repetidas.
- SQLite atende ao protótipo, mas não é indicado para alto volume ou múltiplas instâncias.
- O agendador roda no mesmo processo da aplicação. Use apenas um worker para evitar disputas; produção deve usar uma fila/agendador dedicado.
- Horários são armazenados sem informação de fuso no SQLite e interpretados no fuso configurado da aplicação.
- O mock simula entrega imediata; não simula latência, falhas ou leitura.
- O feedback via WhatsApp usa um formato textual simples.
- As imagens geradas são provisórias e devem ser substituídas após revisão de acessibilidade e conteúdo.
- A validação de assinatura depende de a URL pública vista pela Twilio corresponder à URL recebida pela aplicação.

## Melhorias futuras

- Sessões administrativas, perfis e trilha de auditoria.
- Fluxo de feedback conversacional passo a passo.
- Templates aprovados e localização por campanha.
- Fila externa, retentativas e política de idempotência distribuída.
- Exportação anonimizada de resultados para análise acadêmica.
- Criptografia de campos pessoais e rotina de retenção/exclusão.
- Métricas de falha e alertas operacionais sem rastreamento desnecessário.
- Testes de acessibilidade automatizados e validação com participantes reais.

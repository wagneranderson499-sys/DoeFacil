# DoaFácil 💚 — versão 1.0 (Python)

Um sistema web de doações de objetos entre pessoas, criado como projeto acadêmico. O protótipo HTML anterior foi transformado em um **sistema com back-end real**, banco de dados local, cadastro, login, fotos e fluxo de solicitações.

## Atualização visual: fotos reais

Os anúncios fictícios, as categorias, a página inicial e a área de login usam **fotografias reais** disponibilizadas no Unsplash, em vez de desenhos SVG. As imagens dependem de internet, mas as fotos que os usuários enviarem continuarão guardadas e exibidas localmente. O banco SQLite existente não precisa ser apagado. Veja [créditos e fontes das fotografias](CREDITOS_FOTOS.md).

## Tecnologias

- **Python + Flask**: rotas, autenticação, validações e regras de negócio.
- **SQLite**: banco de dados que funciona sem instalar servidor adicional.
- **HTML + Jinja2 + CSS + JavaScript**: páginas responsivas sem precisar de React/Node.js.
- **Pillow**: valida e reduz fotos enviadas pelos usuários.

## Como executar (Windows, PowerShell)

1. Extraia o `.zip` e abra a pasta `DoaFacil_Python` no VS Code.
2. Abra o terminal na pasta do projeto.
3. Execute os comandos abaixo, um de cada vez:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

> Se o PowerShell bloquear a ativação, você pode **não ativar** e usar `\.venv\Scripts\python.exe -m pip install -r requirements.txt` e depois `\.venv\Scripts\python.exe app.py`. Também é possível usar `py` no lugar de `python` na criação do ambiente.

4. Abra **http://127.0.0.1:5000** no navegador.
5. Para encerrar o servidor, pressione `Ctrl+C`.

### No macOS ou Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Contas de demonstração (APENAS uso local!)

O banco é criado automaticamente e na primeira execução são cadastrados **itens e usuários fictícios**.

| Perfil | E-mail | Senha |
|---|---|---|
| Doadora | `ana@exemplo.com` | `Demo@123` |
| Interessado/doador | `joao@exemplo.com` | `Demo@123` |
| Administradora | `admin@doafacil.local` | `Demo@123` |

**Nunca coloque essas credenciais de demonstração em um servidor público.** Elas servem somente para o trabalho acadêmico e os testes locais.

### Como testar o fluxo completo

1. Entre como `joao@exemplo.com` e acesse **Explorar doações**.
2. Abra **Mochila escolar azul** (foi anunciada por Ana) e clique em **Tenho interesse**.
3. Saia e entre como `ana@exemplo.com`.
4. Vá em **Solicitações → Pedidos recebidos** e clique em **Aprovar**.
5. O status da mochila muda para **Reservado**; somente a solicitação aprovada mostra o e-mail de contato.
6. Em **Minhas doações**, Ana pode clicar em **Confirmar entrega**, mudando o item para **Doado**.
7. Entre como `admin@doafacil.local` para testar o gerenciamento básico de usuários e anúncios.

## Páginas implementadas

- `/` — Página inicial com estatísticas, categorias e itens recentes.
- `/doacoes` — Buscar e filtrar por categoria e cidade.
- `/doacoes/<id>` — Detalhes do item e solicitação.
- `/cadastrar` e `/entrar` — Cadastro e login com senhas protegidas por hash.
- `/painel` — Resumo do usuário autenticado.
- `/doacoes/nova` — Publicação com foto (opcional).
- `/minhas-doacoes` — Editar, excluir e concluir doações.
- `/solicitacoes` — Pedidos enviados/recebidos, aprovação, recusa e cancelamento.
- `/admin` — Painel restrito para contas administrativas.

## Regras do sistema

- Não se pode solicitar o próprio item.
- Um mesmo usuário não pode criar pedidos pendentes duplicados para um anúncio.
- Ao aprovar uma solicitação, o anúncio fica **Reservado** e os outros pedidos pendentes são **Recusados**.
- Só o dono do anúncio pode aprovar, recusar e concluir a doação.
- E-mails de contato só ficam visíveis entre os envolvidos **depois da aprovação**.
- A confirmação de entrega marca a doação como **Doado**.
- O administrador pode bloquear usuários e ocultar anúncios.
- Não existem pagamentos, entregas pelo sistema, chat ou mapa de endereços (fora do escopo).

## Estrutura

```text
DoaFacil_Python/
├── app.py                 # Servidor Flask e regras de negócio
├── schema.sql             # Tabelas e relacionamentos do banco de dados
├── requirements.txt       # Dependências
├── README.md              # Este guia
├── .gitignore             # Ignora banco, uploads e senhas locais
├── .env.example           # Exemplo de variáveis de ambiente
├── templates/             # Páginas HTML usando Jinja2
│   ├── base.html
│   ├── home.html
│   ├── explore.html
│   ├── detail.html
│   ├── auth.html
│   ├── dashboard.html
│   ├── donation_form.html
│   ├── mine.html
│   ├── requests.html
│   ├── admin.html
│   └── error.html
└── static/
    ├── css/style.css
    ├── js/app.js
    ├── img/              # Ilustrações de exemplo
    └── uploads/          # Fotos enviadas (ignoradas pelo Git)
```

O banco local é criado em `instance/doafacil.sqlite3` e **não deve ser colocado no Git**. Os arquivos de imagens enviados também ficam apenas na máquina local.

## Criar seu repositório GitHub

Depois de criar um repositório **vazio** no GitHub, abra o terminal na pasta `DoaFacil_Python`:

```powershell
git init
git add .
git commit -m "Versão inicial do DoaFácil em Python e Flask"
git branch -M main
git remote add origin https://github.com/SEU-USUARIO/DoaFacil.git
git push -u origin main
```

Substitua a URL de exemplo pela URL **real** do repositório que você criar. Se o repositório já tiver arquivos como README, será preciso integrar as alterações, em vez de tentar substituir tudo.

## Próximos incrementos (não implementados ainda)

- Recuperação de senha, confirmação de e-mail e política de privacidade completa.
- Testes automatizados e melhorias de acessibilidade.
- Configuração de produção (HTTPS, limitação de tentativas de login, backups, logs e revisão de segurança).
- PostgreSQL e armazenamento de fotos em nuvem, se o sistema crescer.

### Importante: demonstração x produção

O sistema foi construído **para desenvolvimento local e apresentação acadêmica**. Para publicar na internet, é necessário remover as contas de demonstração, definir a variável de ambiente `SECRET_KEY` com um valor secreto forte, usar HTTPS e implementar controles adicionais (por exemplo, limitação de tentativas de login, confirmação de e-mail, gestão de dados pessoais e armazenamento persistente de fotos). Configure `DEMO_DATA=0` em um banco novo para não criar contas de exemplo.

### Resetar somente os dados de demonstração

Pare o servidor, exclua o arquivo `instance/doafacil.sqlite3` e execute `python app.py` novamente. **Isso apaga todas as contas, anúncios e solicitações locais.**

## Testes automatizados

Depois de instalar as dependências, execute:

```powershell
python -m unittest discover -s tests -v
```

Os testes cobrem a proteção CSRF, áreas restritas e o fluxo completo de solicitação, aprovação e conclusão de uma doação.

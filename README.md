# API de Biblioteca

API REST JSON para cadastrar livros e controlar empréstimos, feita com Python, Django e SQLite. O projeto não usa páginas, templates, CSS ou JavaScript.

## Executar no Windows

No PowerShell, dentro da pasta do projeto:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Se o PowerShell bloquear a ativação do ambiente virtual, execute os comandos seguintes usando o Python dentro dele: `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`, `.\.venv\Scripts\python.exe manage.py migrate` e `.\.venv\Scripts\python.exe manage.py runserver`.

A API ficará disponível em `http://127.0.0.1:8000`. O SQLite cria o arquivo `db.sqlite3` na primeira execução das migrations.

## Rotas

| Método | Rota | Ação |
| --- | --- | --- |
| GET | `/books` | Lista os livros |
| GET | `/books/available` | Lista os livros disponíveis |
| GET | `/books/{id}` | Retorna um livro |
| POST | `/books` | Cadastra um livro |
| PUT | `/books/{id}` | Atualiza todos os campos editáveis do livro |
| DELETE | `/books/{id}` | Remove um livro e os empréstimos relacionados |
| GET | `/loans` | Lista os empréstimos |
| GET | `/loans/{id}` | Retorna um empréstimo |
| POST | `/loans` | Registra um empréstimo |
| PUT | `/loans/{id}` | Atualiza o empréstimo ou registra sua devolução |
| DELETE | `/loans/{id}` | Remove um empréstimo; se ele estava ativo, libera o livro |

Envie `Content-Type: application/json` nas requisições com corpo. Exemplo para cadastrar um livro:

```json
{
  "title": "Clean Code",
  "author": "Robert C. Martin",
  "year": 2008,
  "available": true
}
```

Exemplo para registrar empréstimo:

```json
{
  "book_id": 1,
  "person_name": "João da Silva",
  "loan_date": "2026-10-07"
}
```

Para registrar a devolução com `PUT /loans/{id}`, envie `book_id`, `person_name`, `loan_date` e `return_date`. Para indicar que o empréstimo continua ativo, use `"return_date": null`. As requisições `PUT` substituem os campos editáveis do recurso.

Um livro emprestado fica indisponível. Um segundo empréstimo ativo para o mesmo livro é recusado. Registrar `return_date` libera o livro. Datas usam o formato `YYYY-MM-DD`; erros de validação são retornados em JSON com status `400`, e recursos inexistentes retornam `404`.

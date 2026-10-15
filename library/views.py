import json
from datetime import date

from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import Book, Loan


def _error(message, status=400):
    return JsonResponse({"error": message}, status=status)


def _read_json(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, _error("O corpo da requisição deve conter um JSON válido.")

    if not isinstance(data, dict):
        return None, _error("O corpo da requisição deve ser um objeto JSON.")
    return data, None


def _validate_fields(data, allowed, required):
    unknown = set(data) - set(allowed)
    if unknown:
        return _error(f"Campo(s) não permitido(s): {', '.join(sorted(unknown))}.")

    missing = set(required) - set(data)
    if missing:
        return _error(f"Campo(s) obrigatório(s): {', '.join(sorted(missing))}.")
    return None


def _book_values(data, *, partial=False):
    allowed = {"title", "author", "year", "available"}
    required = {"title", "author", "year"}
    if not partial:
        required.add("available")
    error = _validate_fields(data, allowed, required)
    if error:
        return None, error

    values = {}
    for field in ("title", "author"):
        if field not in data:
            continue
        value = data[field]
        if not isinstance(value, str) or not value.strip():
            return None, _error(f"'{field}' deve ser um texto não vazio.")
        values[field] = value.strip()

    if "year" in data:
        year = data["year"]
        if isinstance(year, bool) or not isinstance(year, int) or year < 1:
            return None, _error("'year' deve ser um número inteiro maior que zero.")
        values["year"] = year

    if "available" in data:
        available = data["available"]
        if not isinstance(available, bool):
            return None, _error("'available' deve ser true ou false.")
        values["available"] = available

    return values, None


def _parse_date(value, field):
    if (
        not isinstance(value, str)
        or len(value) != 10
        or value[4] != "-"
        or value[7] != "-"
    ):
        return None, _error(f"'{field}' deve estar no formato YYYY-MM-DD.")
    try:
        return date.fromisoformat(value), None
    except ValueError:
        return None, _error(f"'{field}' deve estar no formato YYYY-MM-DD.")


def _loan_values(data, *, creating):
    allowed = {"book_id", "person_name", "loan_date"}
    required = set(allowed)
    if not creating:
        allowed.add("return_date")
        required.add("return_date")

    error = _validate_fields(data, allowed, required)
    if error:
        return None, error

    book_id = data["book_id"]
    if isinstance(book_id, bool) or not isinstance(book_id, int) or book_id < 1:
        return None, _error("'book_id' deve ser um número inteiro positivo.")

    person_name = data["person_name"]
    if not isinstance(person_name, str) or not person_name.strip():
        return None, _error("'person_name' deve ser um texto não vazio.")

    loan_date, error = _parse_date(data["loan_date"], "loan_date")
    if error:
        return None, error

    return_date = None
    if not creating:
        raw_return_date = data["return_date"]
        if raw_return_date is not None:
            return_date, error = _parse_date(raw_return_date, "return_date")
            if error:
                return None, error

    return {
        "book_id": book_id,
        "person_name": person_name.strip(),
        "loan_date": loan_date,
        "return_date": return_date,
    }, None


def _book_json(book):
    return {
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "year": book.year,
        "available": book.available,
        "created_at": book.created_at.isoformat(),
    }


def _loan_json(loan):
    return {
        "id": loan.id,
        "book": loan.book_id,
        "person_name": loan.person_name,
        "loan_date": loan.loan_date.isoformat(),
        "return_date": loan.return_date.isoformat() if loan.return_date else None,
    }


@csrf_exempt
def books(request):
    if request.method == "GET":
        return JsonResponse([_book_json(book) for book in Book.objects.all()], safe=False)

    if request.method == "POST":
        data, error = _read_json(request)
        if error:
            return error
        values, error = _book_values(data, partial=True)
        if error:
            return error
        book = Book.objects.create(**values)
        return JsonResponse(_book_json(book), status=201)

    return _error("Método não permitido.", status=405)


@csrf_exempt
def available_books(request):
    if request.method != "GET":
        return _error("Método não permitido.", status=405)
    books = Book.objects.filter(available=True)
    return JsonResponse([_book_json(book) for book in books], safe=False)


@csrf_exempt
def book_detail(request, book_id):
    try:
        book = Book.objects.get(pk=book_id)
    except Book.DoesNotExist:
        return _error("Livro não encontrado.", status=404)

    if request.method == "GET":
        return JsonResponse(_book_json(book))

    if request.method == "PUT":
        data, error = _read_json(request)
        if error:
            return error
        values, error = _book_values(data)
        if error:
            return error

        if values["available"] and Loan.objects.filter(
            book=book, return_date__isnull=True
        ).exists():
            return _error("O livro possui um empréstimo ativo e não pode ficar disponível.")

        for field, value in values.items():
            setattr(book, field, value)
        book.save(update_fields=list(values))
        return JsonResponse(_book_json(book))

    if request.method == "DELETE":
        book.delete()
        return HttpResponse(status=204)

    return _error("Método não permitido.", status=405)


@csrf_exempt
def loans(request):
    if request.method == "GET":
        return JsonResponse(
            [_loan_json(loan) for loan in Loan.objects.select_related("book").all()],
            safe=False,
        )

    if request.method == "POST":
        data, error = _read_json(request)
        if error:
            return error
        values, error = _loan_values(data, creating=True)
        if error:
            return error

        try:
            with transaction.atomic():
                book = Book.objects.select_for_update().get(pk=values["book_id"])
                if not book.available or Loan.objects.filter(
                    book=book, return_date__isnull=True
                ).exists():
                    return _error("O livro não está disponível para empréstimo.")
                loan = Loan.objects.create(
                    book=book,
                    person_name=values["person_name"],
                    loan_date=values["loan_date"],
                )
                book.available = False
                book.save(update_fields=["available"])
        except Book.DoesNotExist:
            return _error("Livro não encontrado.", status=404)

        return JsonResponse(_loan_json(loan), status=201)

    return _error("Método não permitido.", status=405)


@csrf_exempt
def loan_detail(request, loan_id):
    try:
        loan = Loan.objects.select_related("book").get(pk=loan_id)
    except Loan.DoesNotExist:
        return _error("Empréstimo não encontrado.", status=404)

    if request.method == "GET":
        return JsonResponse(_loan_json(loan))

    if request.method == "PUT":
        data, error = _read_json(request)
        if error:
            return error
        values, error = _loan_values(data, creating=False)
        if error:
            return error

        was_active = loan.return_date is None
        old_book = loan.book
        try:
            with transaction.atomic():
                new_book = Book.objects.select_for_update().get(pk=values["book_id"])

                if values["return_date"] is None:
                    other_active_loans = Loan.objects.filter(
                        book=new_book, return_date__isnull=True
                    ).exclude(pk=loan.pk)
                    is_same_active_loan = was_active and new_book.pk == old_book.pk
                    if not is_same_active_loan and (
                        not new_book.available or other_active_loans.exists()
                    ):
                        return _error("O livro não está disponível para empréstimo.")

                loan.book = new_book
                loan.person_name = values["person_name"]
                loan.loan_date = values["loan_date"]
                loan.return_date = values["return_date"]
                loan.save(update_fields=["book", "person_name", "loan_date", "return_date"])

                if was_active and old_book.pk != new_book.pk:
                    if not Loan.objects.filter(
                        book=old_book, return_date__isnull=True
                    ).exists():
                        old_book.available = True
                        old_book.save(update_fields=["available"])

                if values["return_date"] is None:
                    new_book.available = False
                    new_book.save(update_fields=["available"])
                elif was_active and old_book.pk == new_book.pk:
                    if not Loan.objects.filter(
                        book=new_book, return_date__isnull=True
                    ).exists():
                        new_book.available = True
                        new_book.save(update_fields=["available"])
        except Book.DoesNotExist:
            return _error("Livro não encontrado.", status=404)

        return JsonResponse(_loan_json(loan))

    if request.method == "DELETE":
        book = loan.book
        was_active = loan.return_date is None
        loan.delete()
        if was_active and not Loan.objects.filter(
            book=book, return_date__isnull=True
        ).exists():
            book.available = True
            book.save(update_fields=["available"])
        return HttpResponse(status=204)

    return _error("Método não permitido.", status=405)


def bad_request(request, exception=None):
    return _error("Requisição inválida.", status=400)


def permission_denied(request, exception=None):
    return _error("Acesso negado.", status=403)


def not_found(request, exception=None):
    return _error("Rota não encontrada.", status=404)


def server_error(request):
    return _error("Erro interno do servidor.", status=500)

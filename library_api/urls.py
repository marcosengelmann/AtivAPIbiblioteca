from django.urls import path

from library import views


urlpatterns = [
    # Keep this before /books/<id>, so "available" is not interpreted as an ID.
    path("books/available", views.available_books, name="available-books"),
    path("books", views.books, name="books"),
    path("books/<int:book_id>", views.book_detail, name="book-detail"),
    path("loans", views.loans, name="loans"),
    path("loans/<int:loan_id>", views.loan_detail, name="loan-detail"),
]


handler400 = "library.views.bad_request"
handler403 = "library.views.permission_denied"
handler404 = "library.views.not_found"
handler500 = "library.views.server_error"

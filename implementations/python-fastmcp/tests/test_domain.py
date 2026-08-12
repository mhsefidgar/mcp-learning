"""Unit tests for the domain layer — no MCP involved (15-testing/server-testing.md)."""
import pytest

from orders.domain import DomainError, OrderBook


def test_create_order():
    book = OrderBook()
    order = book.create("widget", 2)
    assert order.order_id == "ord-1"
    assert order.total == 20
    assert order.status == "created"


def test_create_validation():
    book = OrderBook()
    with pytest.raises(DomainError):
        book.create("", 1)
    with pytest.raises(DomainError):
        book.create("widget", 0)
    with pytest.raises(DomainError):
        book.create("widget", 101)


def test_ship_flow():
    book = OrderBook()
    order = book.create("widget", 1)
    book.ship(order.order_id)
    assert book.get(order.order_id).status == "shipped"


def test_ship_twice_rejected():
    book = OrderBook()
    order = book.create("widget", 1)
    book.ship(order.order_id)
    with pytest.raises(DomainError):
        book.ship(order.order_id)


def test_unknown_order():
    book = OrderBook()
    with pytest.raises(DomainError):
        book.get("ord-999")

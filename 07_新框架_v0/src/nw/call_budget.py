"""SQLite adaptation of ACCOS BudgetLedger.reserve/settle; unknown charges keep their hold."""
from dataclasses import asdict
from decimal import Decimal, InvalidOperation
import json
import sqlite3
from uuid import uuid4

from nw.store import Store
from nw.task_models import Budget, canonical, response_json


class BudgetExceeded(ValueError):
    pass


def _money(value: str | int | float) -> Decimal:
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        raise ValueError('Invalid budget amount') from None
    if not result.is_finite() or result < 0:
        raise ValueError('Budget amounts must be finite and nonnegative')
    return result


def _amount(value: Decimal) -> str:
    return format(value.normalize(), 'f')


def create_budget(store: Store, budget_id: str, budget: Budget) -> str:
    with store.connection:
        return _insert_budget(store, budget_id, budget)


def _insert_budget(store: Store, budget_id: str, budget: Budget) -> str:
    if (not budget_id or any(type(n) is not int or n < 1 for n in
                             (budget.max_calls, budget.context_char_limit, budget.output_limit))
            or type(budget.max_revisions) is not int or not 0 <= budget.max_revisions <= 2
            or budget.used_calls != 0 or budget.reserved_calls != 0):
        raise ValueError('Invalid new budget limits')
    price = budget.price_snapshot
    if price is not None:
        if (not isinstance(price, dict) or set(price) != {'input_per_token', 'output_per_token', 'currency'}
                or not isinstance(price['currency'], str) or not price['currency'].strip()):
            raise ValueError('Price snapshot requires currency and both token rates')
        for key in ('input_per_token', 'output_per_token'):
            _money(price[key])
    if budget.max_cost is not None:
        if price is None:
            raise ValueError('A cost limit requires a known price snapshot')
        _money(budget.max_cost)
    limits = canonical({k: v for k, v in asdict(budget).items() if k not in ('used_calls', 'reserved_calls')})
    store.connection.execute('INSERT INTO budgets(id,limits_json) VALUES (?,?)', (budget_id, limits))
    return budget_id


def extend_budget(store: Store, budget_id: str, max_calls: int | None, max_cost: str | None) -> None:
    if max_calls is None and max_cost is None:
        return
    with store.connection:
        store.connection.execute('BEGIN IMMEDIATE')
        row = _budget(store, budget_id)
        limits = json.loads(row['limits_json'])
        if max_calls is not None:
            if type(max_calls) is not int or not limits['max_calls'] <= max_calls <= 2**63 - 1:
                raise ValueError('New call ceiling must be at least the original ceiling')
            limits['max_calls'] = max_calls
        if max_cost is not None:
            if limits['max_cost'] is None or _money(max_cost) < _money(limits['max_cost']):
                raise ValueError('A budget extension must raise an existing cost ceiling')
            limits['max_cost'] = max_cost
        store.connection.execute('UPDATE budgets SET limits_json=? WHERE id=?', (canonical(limits), budget_id))


def _budget(store: Store, budget_id: str) -> sqlite3.Row:
    row = store.connection.execute('SELECT * FROM budgets WHERE id=?', (budget_id,)).fetchone()
    if row is None:
        raise ValueError(f'Budget not found: {budget_id}')
    return row


def read_budget(store: Store, budget_id: str) -> Budget:
    row = _budget(store, budget_id)
    return Budget(**json.loads(row['limits_json']), used_calls=row['used_calls'], reserved_calls=row['reserved_calls'])


def _cost(price: dict, input_tokens: int, output_tokens: int) -> Decimal:
    return _money(price['input_per_token']) * input_tokens + _money(price['output_per_token']) * output_tokens


def prepare_call(store: Store, budget_id: str | None, provider: str,
                 params: dict, messages: list[dict]) -> tuple[dict, dict]:
    effective = dict(params)
    if budget_id is None:
        return effective, {}
    budget = read_budget(store, budget_id)
    chars = sum(len(msg['content']) for msg in messages)
    if chars > budget.context_char_limit:
        raise BudgetExceeded('CONTEXT_TOO_LARGE')
    keys = set(effective) & {'num_predict', 'max_tokens', 'max_completion_tokens'}
    allowed = {'num_predict'} if provider == 'ollama' else {'max_tokens', 'max_completion_tokens'}
    if len(keys) > 1 or keys - allowed:
        raise ValueError('Conflicting or unsupported provider output limits')
    key = next(iter(keys), 'num_predict' if provider == 'ollama' else 'max_tokens')
    requested = effective.get(key, budget.output_limit)
    if type(requested) is not int or requested < 1:
        raise ValueError('Output limit must be a positive integer')
    effective[key] = min(requested, budget.output_limit)
    # Adapted from ACCOS ModelRuntime._route; estimate only, not a vendor tokenizer.
    estimate = {'input_tokens': len(canonical(messages).encode('utf-8')) + 64 * len(messages),
                'output_tokens': effective[key], 'context_chars': chars}
    return effective, estimate


def _reserve(store: Store, budget_id: str | None, call_kind: str, call_id: str, estimate: dict) -> str | None:
    """Caller holds a write transaction; freeze the call record in the same transaction."""
    if reservation(store, call_kind, call_id) is not None:
        return None
    estimate = dict(estimate)
    if budget_id is not None:
        row = _budget(store, budget_id)
        limits = json.loads(row['limits_json'])
        if row['used_calls'] + row['reserved_calls'] >= limits['max_calls']:
            raise BudgetExceeded('CALL_LIMIT')
        cost = Decimal(0)
        if limits['price_snapshot'] is not None:
            counts = [estimate.get(key) for key in ('input_tokens', 'output_tokens')]
            if any(type(n) is not int or n < 0 for n in counts):
                raise ValueError('Priced reservations require both token estimates')
            cost = _cost(limits['price_snapshot'], *counts)
        reserved = _money(row['reserved_cost']) + cost
        if limits['max_cost'] is not None and reserved + _money(row['spent_cost']) > _money(limits['max_cost']):
            raise BudgetExceeded('COST_LIMIT')
        estimate['cost'] = _amount(cost) if limits['price_snapshot'] is not None else None
        store.connection.execute(
            'UPDATE budgets SET reserved_calls=reserved_calls+1,reserved_cost=? WHERE id=?',
            (_amount(reserved), budget_id))
    reservation_id = uuid4().hex
    store.connection.execute(
        "INSERT INTO call_reservations(id,budget_id,call_kind,call_id,status,estimate_json) VALUES (?,?,?,?,'STARTED',?)",
        (reservation_id, budget_id, call_kind, call_id, canonical(estimate)))
    return reservation_id


def reserve_call(store: Store, budget_id: str, call_kind: str, call_id: str, estimate: dict) -> bool:
    with store.connection:
        store.connection.execute('BEGIN IMMEDIATE')
        try:
            return _reserve(store, budget_id, call_kind, call_id, estimate) is not None
        except BudgetExceeded:
            return False


def reservation(store: Store, call_kind: str, call_id: str) -> sqlite3.Row | None:
    return store.connection.execute(
        'SELECT * FROM call_reservations WHERE call_kind=? AND call_id=?', (call_kind, call_id)).fetchone()


def _settle(store: Store, reservation_id: str, actual: dict, outcome: str) -> None:
    if outcome not in ('FINISHED', 'UNKNOWN'):
        raise ValueError('Invalid reservation outcome')
    row = store.connection.execute('SELECT * FROM call_reservations WHERE id=?', (reservation_id,)).fetchone()
    if row is None:
        raise ValueError('Unknown reservation')
    if row['status'] == 'FINISHED':
        return
    actual = dict(actual)
    if row['budget_id'] is not None and outcome == 'FINISHED':
        budget = _budget(store, row['budget_id'])
        price = json.loads(budget['limits_json'])['price_snapshot']
        reserved, spent = _money(budget['reserved_cost']), _money(budget['spent_cost'])
        if price is not None:
            counts = (actual.get('prompt_tokens', actual.get('prompt_eval_count')),
                      actual.get('completion_tokens', actual.get('eval_count')))
            if not all(type(n) is int and n >= 0 for n in counts):
                # A response can be retained while its billing remains unreconciled.
                outcome = 'UNKNOWN'
                actual['cost'] = None
            else:
                cost = _cost(price, *counts)
                reserved -= _money(json.loads(row['estimate_json'])['cost'])
                spent += cost
                actual['cost'] = _amount(cost)
        if outcome == 'FINISHED':
            store.connection.execute(
                'UPDATE budgets SET reserved_calls=reserved_calls-1,used_calls=used_calls+1,'
                'reserved_cost=?,spent_cost=? WHERE id=?', (_amount(reserved), _amount(spent), row['budget_id']))
    store.connection.execute('UPDATE call_reservations SET status=?,actual_json=? WHERE id=?',
                             (outcome, response_json(actual), reservation_id))


def finish_reservation(store: Store, reservation_id: str, actual: dict, outcome: str) -> None:
    with store.connection:
        store.connection.execute('BEGIN IMMEDIATE')
        _settle(store, reservation_id, actual, outcome)

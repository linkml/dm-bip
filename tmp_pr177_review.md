**Review: Approve**

Clean, well-scoped fix. The production code change is 4 lines and does exactly what it should:

1. `use_key=True` — the `SchemaView.get_identifier_slot()` API already supports falling back to `key: true` slots; the old call just wasn't using it.
2. `if id_slot is not None:` guard — correct behavior when a class has neither `identifier` nor `key` (the new `NO_ID_SCHEMA` test covers exactly this case). The old code would have crashed with `AttributeError: 'NoneType' object has no attribute 'name'`.

Both new tests are meaningful: one exercises `key: true`, one exercises the no-id/no-key path. The existing `test_dynamic_object` continues to cover the `identifier: true` path.

Our production bdchm schema uses `identifier: true` on one class, so this bug was not triggered by our pipeline today — but the guard is the right defensive behavior regardless. 7/7 CI checks pass.

# Answer Passport key rotation

Rotation registers a new pending public record, validates provider correspondence by signing a
fixed domain-purpose challenge, yields a cancellation point, then atomically activates the usable
new key and retires the old active key. Generation increases monotonically, links are updated, and
the historical record is retained. Competing operations serialize at the registry mutation; at
most one active record is visible. Bundle generation sees either the before or after snapshot.

A pending future key cannot activate before `not_before`; explicit activation never retires the
current key until the replacement is validated and usable. Cancellation before atomic commit can
leave a harmless pending record, never a partly active record. Production version allocation and
durable transactions are Phase 3B work.

"""Global Secondary Index support for pydynox models.

GSIs allow querying by non-key attributes. Define them on your model
and query using the index's partition key.

Example:
    >>> from pydynox import Model, ModelConfig
    >>> from pydynox.attributes import StringAttribute
    >>> from pydynox.indexes import GlobalSecondaryIndex
    >>>
    >>> class User(Model):
    ...     model_config = ModelConfig(table="users")
    ...     pk = StringAttribute(hash_key=True)
    ...     sk = StringAttribute(range_key=True)
    ...     email = StringAttribute()
    ...     status = StringAttribute()
    ...
    ...     # Define GSIs
    ...     email_index = GlobalSecondaryIndex(
    ...         index_name="email-index",
    ...         hash_key="email",
    ...     )
    ...     status_index = GlobalSecondaryIndex(
    ...         index_name="status-index",
    ...         hash_key="status",
    ...         range_key="pk",
    ...     )
    >>>
    >>> # Query by email
    >>> for user in User.email_index.query(email="john@example.com"):
    ...     print(user.pk)
    >>>
    >>> # Query by status with sort key condition
    >>> for user in User.status_index.query(
    ...     status="active",
    ...     range_key_condition=User.pk.begins_with("USER#"),
    ... ):
    ...     print(user.email)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    from pydynox.conditions import Condition
    from pydynox.model import Model

M = TypeVar("M", bound="Model")

__all__ = ["GlobalSecondaryIndex"]


class GlobalSecondaryIndex(Generic[M]):
    """Global Secondary Index definition for a Model.

    GSIs let you query by attributes other than the table's primary key.
    Define them as class attributes on your Model.

    Args:
        index_name: Name of the GSI in DynamoDB.
        hash_key: Attribute name to use as the GSI partition key.
        range_key: Optional attribute name for the GSI sort key.
        projection: Attributes to project. Options:
            - "ALL" (default): All attributes
            - "KEYS_ONLY": Only key attributes
            - list of attribute names: Specific attributes

    Example:
        >>> class User(Model):
        ...     model_config = ModelConfig(table="users")
        ...     pk = StringAttribute(hash_key=True)
        ...     email = StringAttribute()
        ...
        ...     email_index = GlobalSecondaryIndex(
        ...         index_name="email-index",
        ...         hash_key="email",
        ...     )
        >>>
        >>> # Query the index
        >>> users = User.email_index.query(email="john@example.com")
    """

    def __init__(
        self,
        index_name: str,
        hash_key: str,
        range_key: str | None = None,
        projection: str | list[str] = "ALL",
    ) -> None:
        """Create a GSI definition.

        Args:
            index_name: Name of the GSI in DynamoDB.
            hash_key: Attribute name for the GSI partition key.
            range_key: Optional attribute name for the GSI sort key.
            projection: Projection type or list of attributes.
        """
        self.index_name = index_name
        self.hash_key = hash_key
        self.range_key = range_key
        self.projection = projection

        # Set by Model metaclass
        self._model_class: type[M] | None = None
        self._attr_name: str | None = None

    def __set_name__(self, owner: type[M], name: str) -> None:
        """Called when the descriptor is assigned to a class attribute."""
        self._attr_name = name

    def _bind_to_model(self, model_class: type[M]) -> None:
        """Bind this index to a model class."""
        self._model_class = model_class

    def _get_model_class(self) -> type[M]:
        """Get the bound model class or raise error."""
        if self._model_class is None:
            raise RuntimeError(
                f"GSI '{self.index_name}' is not bound to a model. "
                "Make sure it's defined as a class attribute on a Model subclass."
            )
        return self._model_class

    def query(
        self,
        range_key_condition: Condition | None = None,
        filter_condition: Condition | None = None,
        limit: int | None = None,
        scan_index_forward: bool = True,
        **key_values: Any,
    ) -> GSIQueryResult[M]:
        """Query the GSI.

        Args:
            range_key_condition: Optional condition on the GSI range key.
                Use attribute comparison methods like `begins_with`, `between`, etc.
            filter_condition: Optional filter on non-key attributes.
                Applied after the query, still consumes RCU for filtered items.
            limit: Max items per page (not total).
            scan_index_forward: Sort order. True = ascending (default), False = descending.
            **key_values: The GSI hash key value. Must include the hash_key attribute.

        Returns:
            GSIQueryResult that can be iterated.

        Example:
            >>> # Simple query by hash key
            >>> for user in User.email_index.query(email="john@example.com"):
            ...     print(user.name)
            >>>
            >>> # With range key condition
            >>> for user in User.status_index.query(
            ...     status="active",
            ...     range_key_condition=User.created_at > "2024-01-01",
            ... ):
            ...     print(user.email)
            >>>
            >>> # With filter
            >>> for user in User.email_index.query(
            ...     email="john@example.com",
            ...     filter_condition=User.age >= 18,
            ... ):
            ...     print(user.name)
            >>>
            >>> # Descending order with limit
            >>> for user in User.status_index.query(
            ...     status="active",
            ...     limit=10,
            ...     scan_index_forward=False,
            ... ):
            ...     print(user.email)
        """
        model_class = self._get_model_class()

        # Validate hash key is provided
        if self.hash_key not in key_values:
            raise ValueError(
                f"GSI query requires '{self.hash_key}' (the hash key). "
                f"Got: {list(key_values.keys())}"
            )

        return GSIQueryResult(
            model_class=model_class,
            index_name=self.index_name,
            hash_key=self.hash_key,
            hash_key_value=key_values[self.hash_key],
            range_key=self.range_key,
            range_key_condition=range_key_condition,
            filter_condition=filter_condition,
            limit=limit,
            scan_index_forward=scan_index_forward,
        )

    def to_dynamodb_definition(self) -> dict[str, Any]:
        """Convert to DynamoDB GSI definition format.

        Used when creating tables with GSIs.

        Returns:
            Dict in DynamoDB CreateTable GSI format.
        """
        key_schema = [{"AttributeName": self.hash_key, "KeyType": "HASH"}]
        if self.range_key:
            key_schema.append({"AttributeName": self.range_key, "KeyType": "RANGE"})

        # Build projection
        projection: dict[str, Any]
        if self.projection == "ALL":
            projection = {"ProjectionType": "ALL"}
        elif self.projection == "KEYS_ONLY":
            projection = {"ProjectionType": "KEYS_ONLY"}
        elif isinstance(self.projection, list):
            projection = {
                "ProjectionType": "INCLUDE",
                "NonKeyAttributes": self.projection,
            }
        else:
            projection = {"ProjectionType": "ALL"}

        return {
            "IndexName": self.index_name,
            "KeySchema": key_schema,
            "Projection": projection,
        }


class GSIQueryResult(Generic[M]):
    """Result of a GSI query with automatic pagination.

    Iterate over results to get model instances.
    Access `last_evaluated_key` for manual pagination.
    Access `metrics` for timing and capacity info.

    Example:
        >>> results = User.email_index.query(email="john@example.com")
        >>> for user in results:
        ...     print(user.name)
        >>>
        >>> # Check metrics
        >>> print(results.metrics.duration_ms)
        >>> print(results.metrics.consumed_rcu)
    """

    def __init__(
        self,
        model_class: type[M],
        index_name: str,
        hash_key: str,
        hash_key_value: Any,
        range_key: str | None = None,
        range_key_condition: Condition | None = None,
        filter_condition: Condition | None = None,
        limit: int | None = None,
        scan_index_forward: bool = True,
        last_evaluated_key: dict[str, Any] | None = None,
    ) -> None:
        self._model_class = model_class
        self._index_name = index_name
        self._hash_key = hash_key
        self._hash_key_value = hash_key_value
        self._range_key = range_key
        self._range_key_condition = range_key_condition
        self._filter_condition = filter_condition
        self._limit = limit
        self._scan_index_forward = scan_index_forward
        self._start_key = last_evaluated_key

        # Iteration state
        self._query_result: Any = None
        self._items_iter: Any = None
        self._initialized = False

    @property
    def last_evaluated_key(self) -> dict[str, Any] | None:
        """The last evaluated key for pagination.

        Returns None if all results have been fetched.
        """
        if self._query_result is None:
            return None
        result: dict[str, Any] | None = self._query_result.last_evaluated_key
        return result

    @property
    def metrics(self) -> Any:
        """Metrics from the last page fetch.

        Returns None if no pages have been fetched yet.
        """
        if self._query_result is None:
            return None
        return self._query_result.metrics

    def _build_query(self) -> Any:
        """Build the underlying QueryResult."""
        from pydynox.query import QueryResult

        client = self._model_class._get_client()
        table = self._model_class._get_table()

        # Build key condition expression
        # names: {attr_name: placeholder} - we need to track this for building expression
        # then convert to {placeholder: attr_name} for DynamoDB
        names: dict[str, str] = {}
        values: dict[str, Any] = {}

        # Hash key condition: #gsi_hk = :gsi_hkv
        hk_name_placeholder = "#gsi_hk"
        hk_value_placeholder = ":gsi_hkv"
        names[self._hash_key] = hk_name_placeholder
        values[hk_value_placeholder] = self._hash_key_value

        key_condition = f"{hk_name_placeholder} = {hk_value_placeholder}"

        # Add range key condition if provided
        if self._range_key_condition is not None:
            rk_expr = self._range_key_condition.serialize(names, values)
            key_condition = f"{key_condition} AND {rk_expr}"

        # Build filter expression if provided
        filter_expr = None
        if self._filter_condition is not None:
            filter_expr = self._filter_condition.serialize(names, values)

        # Convert names to DynamoDB format: {placeholder: attr_name}
        attr_names = {placeholder: attr_name for attr_name, placeholder in names.items()}

        return QueryResult(
            client._client,
            table,
            key_condition,
            filter_expression=filter_expr,
            expression_attribute_names=attr_names if attr_names else None,
            expression_attribute_values=values if values else None,
            limit=self._limit,
            scan_index_forward=self._scan_index_forward,
            index_name=self._index_name,
            last_evaluated_key=self._start_key,
            acquire_rcu=client._acquire_rcu,
        )

    def __iter__(self) -> GSIQueryResult[M]:
        return self

    def __next__(self) -> M:
        # Initialize on first iteration
        if not self._initialized:
            self._query_result = self._build_query()
            self._items_iter = iter(self._query_result)
            self._initialized = True

        # Get next item from underlying query
        item = next(self._items_iter)

        # Convert to model instance
        instance = self._model_class.from_dict(item)

        # Run after_load hooks
        skip = (
            self._model_class.model_config.skip_hooks
            if hasattr(self._model_class, "model_config")
            else False
        )
        if not skip:
            from pydynox.hooks import HookType

            instance._run_hooks(HookType.AFTER_LOAD)

        return instance

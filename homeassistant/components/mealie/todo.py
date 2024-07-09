"""Todo platform for Mealie."""

from __future__ import annotations

from aiomealie import MealieError, MutateShoppingItem, ShoppingItem, ShoppingList

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import MealieConfigEntry, MealieShoppingListCoordinator
from .entity import MealieEntity

TODO_STATUS_MAP = {
    False: TodoItemStatus.NEEDS_ACTION,
    True: TodoItemStatus.COMPLETED,
}
TODO_STATUS_MAP_INV = {v: k for k, v in TODO_STATUS_MAP.items()}


def _convert_api_item(item: ShoppingItem) -> TodoItem:
    """Convert Mealie shopping list items into a TodoItem."""

    return TodoItem(
        summary=item.display,
        uid=item.item_id,
        status=TODO_STATUS_MAP.get(
            item.checked,
            TodoItemStatus.NEEDS_ACTION,
        ),
        due=None,
        description=None,
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MealieConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the todo platform for entity."""
    coordinator = entry.runtime_data.shoppinglist_coordinator

    async_add_entities(
        MealieShoppingListTodoListEntity(coordinator, shopping_list)
        for shopping_list in coordinator.shopping_lists
    )


class MealieShoppingListTodoListEntity(MealieEntity, TodoListEntity):
    """A todo list entity."""

    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
        | TodoListEntityFeature.MOVE_TODO_ITEM
    )

    coordinator: MealieShoppingListCoordinator

    def __init__(
        self, coordinator: MealieShoppingListCoordinator, shopping_list: ShoppingList
    ) -> None:
        """Create the todo entity."""
        super().__init__(coordinator, shopping_list.list_id)
        self._shopping_list = shopping_list
        self._attr_name = shopping_list.name
        self._attr_unique_id = (
            f"{self.coordinator.config_entry.entry_id}_{shopping_list.list_id}"
        )
        self.translation_key = "shopping_list"

    @property
    def todo_items(self) -> list[TodoItem] | None:
        """Get the current set of To-do items."""
        if self._shopping_list.list_id in self.coordinator.shopping_list_items:
            return [
                _convert_api_item(item)
                for item in self.coordinator.shopping_list_items[
                    self._shopping_list.list_id
                ]
            ]

        return []

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Add an item to the list."""
        position = 0
        if len(self.coordinator.shopping_list_items[self._shopping_list.list_id]) > 0:
            position = (
                self.coordinator.shopping_list_items[self._shopping_list.list_id][
                    -1
                ].position
                + 1
            )

        new_shopping_item = MutateShoppingItem(
            list_id=self._shopping_list.list_id,
            note=item.summary.strip() if item.summary else item.summary,
            position=position,
        )
        try:
            await self.coordinator.client.add_shopping_item(new_shopping_item)
        except MealieError as exception:
            raise HomeAssistantError(
                f"An error occurred adding an item to {self._shopping_list.name}"
            ) from exception

        await self.coordinator.async_refresh()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Update an item on the list."""
        list_items = self.coordinator.shopping_list_items[self._shopping_list.list_id]

        for items in list_items:
            if items.item_id == item.uid:
                position = items.position
                break

        list_items = self.coordinator.shopping_list_items[self._shopping_list.list_id]

        list_item: ShoppingItem | None = next(
            (x for x in list_items if x.item_id == item.uid), None
        )

        if list_item:
            udpdate_shopping_item = MutateShoppingItem(
                item_id=list_item.item_id,
                list_id=list_item.list_id,
                note=list_item.note,
                display=list_item.display,
                checked=item.status == TodoItemStatus.COMPLETED,
                position=list_item.position,
                is_food=list_item.is_food,
                disable_amount=list_item.disable_amount,
                quantity=list_item.quantity,
                label_id=list_item.label_id,
                food_id=list_item.food_id,
                unit_id=list_item.unit_id,
            )

            stripped_item_summary = (
                item.summary.strip() if item.summary else item.summary
            )

            if list_item.display.strip() != stripped_item_summary:
                udpdate_shopping_item.note = stripped_item_summary
                udpdate_shopping_item.position = position
                udpdate_shopping_item.is_food = False
                udpdate_shopping_item.food_id = None
                udpdate_shopping_item.quantity = 0.0
                udpdate_shopping_item.checked = item.status == TodoItemStatus.COMPLETED

            try:
                await self.coordinator.client.update_shopping_item(
                    list_item.item_id, udpdate_shopping_item
                )
            except MealieError as exception:
                raise HomeAssistantError(
                    f"An error occurred updated an item on {self._shopping_list.name}"
                ) from exception

            await self.coordinator.async_refresh()
            return

        raise HomeAssistantError(f"Item {item.uid} not found in shopping list")

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Delete items from the list."""
        try:
            for uid in uids:
                await self.coordinator.client.delete_shopping_item(uid)
        except MealieError as exception:
            raise HomeAssistantError(
                f"An error occurred deleting item(s) on {self._shopping_list.name}"
            ) from exception

        await self.coordinator.async_refresh()

    async def async_move_todo_item(
        self, uid: str, previous_uid: str | None = None
    ) -> None:
        """Re-order an item on the list."""
        if uid == previous_uid:
            return
        list_items: list[ShoppingItem] = self.coordinator.shopping_list_items[
            self._shopping_list.list_id
        ]

        item_idx = {itm.item_id: idx for idx, itm in enumerate(list_items)}
        if uid not in item_idx:
            raise HomeAssistantError(f"Item '{uid}' not found in shopping list")
        if previous_uid and previous_uid not in item_idx:
            raise HomeAssistantError(
                f"Item '{previous_uid}' not found in shopping list"
            )
        dst_idx = item_idx[previous_uid] + 1 if previous_uid else 0
        src_idx = item_idx[uid]
        src_item = list_items.pop(src_idx)
        if dst_idx > src_idx:
            dst_idx -= 1
        list_items.insert(dst_idx, src_item)

        for position, item in enumerate(list_items):
            mutate_shopping_item = MutateShoppingItem()
            mutate_shopping_item.list_id = item.list_id
            mutate_shopping_item.item_id = item.item_id
            mutate_shopping_item.position = position
            mutate_shopping_item.is_food = item.is_food
            mutate_shopping_item.quantity = item.quantity
            mutate_shopping_item.label_id = item.label_id
            mutate_shopping_item.note = item.note
            mutate_shopping_item.checked = item.checked

            if item.is_food:
                mutate_shopping_item.food_id = item.food_id
                mutate_shopping_item.unit_id = item.unit_id

            await self.coordinator.client.update_shopping_item(
                mutate_shopping_item.item_id, mutate_shopping_item
            )

        await self.coordinator.async_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        self._async_update_attrs()
        super()._handle_coordinator_update()

    @callback
    def _async_update_attrs(self) -> None:
        """Update todo attributes."""

        items = []

        if self._shopping_list.list_id in self.coordinator.shopping_list_items:
            for item in self.coordinator.shopping_list_items[
                self._shopping_list.list_id
            ]:
                todo_item = _convert_api_item(item)
                items.append(todo_item)

        self._attr_todo_items = items

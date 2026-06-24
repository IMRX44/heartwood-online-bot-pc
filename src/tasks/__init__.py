from src.tasks.base import Task, TaskContext
from src.tasks.fishing import FishingTask
from src.tasks.gathering import GatheringTask
from src.tasks.combat import CombatTask
from src.tasks.crafting import CraftingTask

# Registry used by the command parser to instantiate tasks by name.
TASK_REGISTRY = {
    "fish": FishingTask,
    "gather": GatheringTask,
    "farm": CombatTask,
    "combat": CombatTask,
    "craft": CraftingTask,
}

__all__ = [
    "Task", "TaskContext", "TASK_REGISTRY",
    "FishingTask", "GatheringTask", "CombatTask", "CraftingTask",
]

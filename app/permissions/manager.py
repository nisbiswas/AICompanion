from enum import Enum


class Permission(str, Enum):
    BROWSER_CONTEXT = "browser_context"
    BROWSER_PAGE_READ = "browser_page_read"
    WEB_SEARCH = "web_search"
    RESEARCH = "research"
    BROWSER_NAVIGATE = "browser_navigate"
    BROWSER_INTERACT = "browser_interact"


class PermissionManager:
    def __init__(self):
        self._permissions: dict[Permission, bool] = {
            Permission.BROWSER_CONTEXT: False,
            Permission.BROWSER_PAGE_READ: False,
            Permission.WEB_SEARCH: False,
            Permission.RESEARCH: False,
            Permission.BROWSER_NAVIGATE: False,
            Permission.BROWSER_INTERACT: False,
        }

    def grant(self, permission: Permission):
        self._permissions[permission] = True

    def revoke(self, permission: Permission):
        self._permissions[permission] = False

    def is_allowed(self, permission: Permission) -> bool:
        return self._permissions.get(permission, False)

    def require(self, permission: Permission) -> bool:
        return self.is_allowed(permission)

    def snapshot(self) -> dict[str, bool]:
        return {
            permission.value: allowed
            for permission, allowed in self._permissions.items()
        }

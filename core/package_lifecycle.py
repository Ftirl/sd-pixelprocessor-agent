"""Track ownership and cleanup state for agent-created packages."""

class PackageRegistry:
    def __init__(self):
        self.items = {}

    def register(self, package_id, owner="sd-pixelprocessor-agent", kind="temporary"):
        if package_id in self.items and self.items[package_id]["status"] == "created":
            raise ValueError("resource already registered: %s" % package_id)
        self.items[package_id] = {"owner": owner, "kind": kind, "status": "created"}

    def cleanup_temporary(self, cleanup=None):
        """Clean registered temporary resources and record their final state.

        ``cleanup`` receives each resource id and performs host-specific deletion.
        With no callback, no resource is deleted or marked cleaned. Callers should
        leave uncertain/unsaved Designer packages in place and report residue.
        """
        if cleanup is None:
            return []
        cleaned = []
        for package_id, record in self.items.items():
            if record["kind"] != "temporary" or record["status"] != "created":
                continue
            cleanup(package_id)
            record["status"] = "cleaned"
            cleaned.append(package_id)
        return cleaned

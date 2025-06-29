def format_sync_result(result: dict) -> str:
    """Format sync result for display in UI."""
    status = result["status"]
    updates = result["updates"]
    versions = result["versions"]
    errors = result["errors"]

    # Build status message
    if status == "error":
        status_msg = "❌ Sync failed"
    elif status == "updated":
        status_msg = "✅ Sync completed with updates"
    elif status == "no_update_needed":
        status_msg = "ℹ️ No updates needed"
    else:
        status_msg = f"❓ Unknown status: {status}"

    # Build version info
    version_info = []
    if versions["local"]["version"]:
        version_info.append(
            "Local: v{} ({})".format(
                versions["local"]["version"], versions["local"]["date"]
            )
        )
    if versions["remote"]["version"]:
        version_info.append(
            "Remote: v{} ({})".format(
                versions["remote"]["version"], versions["remote"]["date"]
            )
        )

    # Build update info
    update_info = []
    if updates.get("meta", False):
        update_info.append("• Meta.json updated")
    if updates.get("sqlite", False):
        update_info.append("• AllPrintings.sqlite updated")
    if updates.get("keywords", False):
        update_info.append("• Keywords.json updated")
    if updates.get("cardtypes", False):
        update_info.append("• CardTypes.json updated")
    if updates.get("database", False):
        update_info.append("• Database rebuilt")

    # Build error info
    error_info = []
    if errors:
        error_info.append("Errors:")
        for error in errors:
            error_info.append(f"• {error}")

    # Combine all sections
    sections = [status_msg]
    if version_info:
        sections.append("\nVersions:")
        sections.extend(version_info)
    if update_info:
        sections.append("\nUpdates:")
        sections.extend(update_info)
    if error_info:
        sections.append("\n")
        sections.extend(error_info)

    return "\n".join(sections)

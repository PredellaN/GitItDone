from bpy.types import UILayout
import bpy
from . import registry

class GitOperator(bpy.types.Operator):
    bl_idname: str = "wm.git_generic"
    bl_label: str = "Generic Git"

    def default_checks(self, filepath) -> set[str] | None:
        from .instances.git_instance import git
        if not git.repo:
            self.report({'ERROR'}, "No Git repository found.")
            return {'CANCELLED'}
        return None

    def extra_checks(self, filepath) -> set[str] | None:
        return None

    def run_git(self, filepath) -> set[str] | None:
        return None
        
    def execute(self, context): #type: ignore
        filepath = bpy.data.filepath

        if ret := self.default_checks(filepath): return ret
        if ret := self.extra_checks(filepath): return ret
        if ret := self.run_git(filepath): return ret

@registry.register_class
class GitPullOperator(GitOperator):
    bl_idname: str = "wm.git_pull"
    bl_label: str = "Git Pull"

    def run_git(self, filepath) -> set[str] | None:
        from .instances.git_instance import git

        if git.pull():
            self.report({'INFO'}, "Changes pulled.")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "Git pull failed.")
            return {'CANCELLED'}

@registry.register_class
class GitRevertOperator(GitOperator):
    bl_idname: str = "wm.git_revert"
    bl_label: str = "Git Revert"

    def run_git(self, filepath) -> set[str] | None:
        from .instances.git_instance import git
        if git.revert_file(filepath):
            self.report({'INFO'}, "Changes reverted.")
            bpy.ops.wm.revert_mainfile()
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "Git revert failed.")
            return {'CANCELLED'}

@registry.register_class
class CommitGitChangesOperator(GitOperator):
    bl_idname: str = "wm.commit_git_changes"
    bl_label: str = "Commit Git Changes"

    commit_message: bpy.props.StringProperty(
        name="Commit Message",
        default="Committing changes from Blender."
    )

    def extra_checks(self, filepath):
        from .instances.git_instance import git

        if not git.has_file_changes(filepath):
            self.report({'INFO'}, "No changes detected.")
            return {'CANCELLED'}

        if git.will_conflict(filepath):
            self.report({'ERROR'}, "Potential merge conflicts detected. Resolve them before committing.")
            return {'CANCELLED'}

    def run_git(self, filepath):
        from .instances.git_instance import git

        if git.commit_changes(self.commit_message, filepath):
            self.report({'INFO'}, "Changes committed and pushed successfully.")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "Git commit or push failed.")
            return {'CANCELLED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self) #type: ignore

@registry.register_class
class GIT_PT_tools_panel(bpy.types.Panel):
    """Panel to trigger Git commit operations."""
    bl_label: str = "Git Tools"
    bl_idname: str = "GIT_PT_tools_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context: str = "scene"

    def draw(self, context):
        from .instances.git_instance import git

        layout: UILayout | None = self.layout
        if not layout: return

        filepath = bpy.data.filepath

        if not filepath:
            layout.label(text="Please save the blend file first.")
            return

        url = git.remote_url

        layout.label(text=f"Repository Path: {git.repo_path}")
        layout.label(text=f"Repository URL: {url}")
        if not git.repo:
            layout.label(text="The blend file is not part of a Git repository.")
            return
        
        layout.operator("wm.commit_git_changes", text="Commit Changes")
        layout.operator("wm.git_revert", text="Revert Current File")
        layout.operator("wm.git_pull", text="Pull Repository")

def register():
    registry.blender_register_classes()

def unregister():
    registry.blender_unregister_classes()
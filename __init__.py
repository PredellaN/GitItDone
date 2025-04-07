from subprocess import CompletedProcess
from configparser import ConfigParser
import os
import subprocess
import configparser
import bpy #type: ignore
from functools import lru_cache
from . import auto_load

auto_load.init()

@lru_cache
def get_repo(filepath) -> tuple[str | None, str | None]:
    directory: str = os.path.dirname(filepath)
    repo_path: str | None = None
    while directory:
        if os.path.isdir(os.path.join(directory, ".git")):
            repo_path = directory
            break
        parent: str = os.path.dirname(directory)
        if parent == directory:
            break
        directory = parent

    if repo_path:
        config_path: str = os.path.join(repo_path, ".git", "config")
        remote_url: str | None = None
        if os.path.exists(path=config_path):
            config: ConfigParser = configparser.ConfigParser()
            config.read(filenames=config_path)
            
            section = 'remote "origin"'
            if section in config and 'url' in config[section]:
                remote_url = config[section]['url']
        return repo_path, remote_url
    else:
        return None, None

def has_tracked_changes(repo_path):
    try:
        result: CompletedProcess[str] = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return bool(result.stdout.strip())
    except subprocess.CalledProcessError:
        return False

def check_for_conflicts(repo_path):
    try:
        result = subprocess.run(
            ["git", "pull", "--dry-run"],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        # Look for conflict indicators in stdout or stderr
        if "CONFLICT" in result.stdout or "error:" in result.stderr:
            return True
        return False
    except subprocess.CalledProcessError:
        return True

def commit_changes(repo_path, message):
    try:
        subprocess.run(["git", "add", "-A"], cwd=repo_path, check=True)
        subprocess.run(["git", "commit", "-m", message], cwd=repo_path, check=True)
        subprocess.run(["git", "push"], cwd=repo_path, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print("Git operation failed:", e)
        return False

class CommitGitChangesOperator(bpy.types.Operator):
    """Commit and sync changes if part of a Git repository."""
    bl_idname: str = "wm.commit_git_changes"
    bl_label: str = "Commit Git Changes"

    commit_message: bpy.props.StringProperty(
        name="Commit Message",
        default="Committing changes from Blender."
    )

    def execute(self, context):
        repo_path, url = get_repo(bpy.data.filepath)

        if not has_tracked_changes(repo_path):
            self.report({'INFO'}, "No changes detected.")
            return {'CANCELLED'}

        if check_for_conflicts(repo_path):
            self.report({'ERROR'}, "Potential merge conflicts detected. Resolve them before committing.")
            return {'CANCELLED'}

        if commit_changes(repo_path, self.commit_message):
            self.report({'INFO'}, "Changes committed and pushed successfully.")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "Git commit or push failed.")
            return {'CANCELLED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

class GIT_PT_tools_panel(bpy.types.Panel):
    """Panel to trigger Git commit operations."""
    bl_label: str = "Git Tools"
    bl_idname: str = "GIT_PT_tools_panel"
    bl_space_type: str = 'PROPERTIES'
    bl_region_type: str = 'WINDOW'
    bl_context: str = "scene"

    def draw(self, context):
        layout = self.layout
        filepath = bpy.data.filepath

        if not filepath:
            layout.label(text="Please save the blend file first.")
            return

        repo_path, url = get_repo(filepath)

        layout.label(text=f"Repository Path: {repo_path}")
        layout.label(text=f"Repository URL: {url}")
        if not repo_path:
            layout.label(text="The blend file is not part of a Git repository.")
            return
        
        layout.operator("wm.commit_git_changes", text="Commit Git Changes")

def register():
    auto_load.register()
    bpy.utils.register_class(CommitGitChangesOperator)
    bpy.utils.register_class(GIT_PT_tools_panel)

def unregister():
    bpy.utils.unregister_class(GIT_PT_tools_panel)
    bpy.utils.unregister_class(CommitGitChangesOperator)
    auto_load.unregister()

import bpy
import os
from ..functions.git import GitRepo

git = GitRepo(os.path.dirname(bpy.data.filepath))
from .BaseController import BaseController
from .ProjectController import ProjectController
from fastapi import UploadFile
from models import ResponseSignal
import re
import os
class DataController(BaseController):
    def __init__(self):
        super().__init__()
        self.size_scale = 1024*1024 # 1MB
    def validate_file(self, file: UploadFile):
        if file.content_type not in self.app_settings.FILE_ALLOWED_TYPES:
            return False,ResponseSignal.FILE_TYPE_NOT_SUPPORTED.value
        if file.size > self.app_settings.FILE_MAX_SIZE * self.size_scale:
            return False,ResponseSignal.FILE_SIZE_IS_EXCEEDED.value
        return True,ResponseSignal.FILE_VALIDATION_SUCCESS.value

    def generate_unique_file_name(self, orig_file_name: str, project_id: str):
       project_dir = ProjectController().get_project_dir(project_id=project_id)
       random_key = self.generate_random_string(18)
       clean_file_name = self.get_clean_file_name(orig_file_name=orig_file_name)
       new_file_path = os.path.join(project_dir, f"{clean_file_name}_{random_key}")
       while os.path.exists(new_file_path):
           random_key = self.generate_random_string(18)
           new_file_path = os.path.join(project_dir, f"{clean_file_name}_{random_key}")
       return new_file_path

    def get_clean_file_name(self, orig_file_name: str):
        # remove any special characters except a-z, A-Z, 0-9, - and _
        clean_file_name = re.sub(r'[^a-zA-Z0-9_-]', '', orig_file_name)
        #replace spaces with _
        clean_file_name = clean_file_name.replace(' ', '_')
        return clean_file_name
import os
from dotenv import load_dotenv

load_dotenv()

class Config:

    @staticmethod
    def get_config(project, env):
        """
        Dynamically fetch configuration
        based on project and environment.
        """

        project = project.upper()
        env = env.upper()

        config = {
            "url": os.getenv(f"{project}_{env}_URL"),
            "username": os.getenv(f"{project}_{env}_USERNAME"),
            "password": os.getenv(f"{project}_{env}_PASSWORD")
        }

        if not config["url"]:
            raise ValueError(
                f"Configuration not found for "
                f"PROJECT={project} ENV={env}"
            )

        return config
